# Social Media Studio

A backend platform that automates social media content creation and publishing. You give it a blog article URL or raw text, and it generates platform-specific posts (LinkedIn, Twitter, Discord, Facebook, Telegram...) using LLM agents, then publishes them through registered publishers.

---

## Tech Stack

| Layer        | Technology                          |
|--------------|-------------------------------------|
| API          | FastAPI (Python)                    |
| Database     | Supabase (PostgreSQL)               |
| Queue        | PGMQ (PostgreSQL Message Queue)     |
| LLM          | Groq API (openai/gpt-oss-20b)           |
| Storage      | Supabase Storage (S3-compatible)    |
| Auth         | Supabase Auth (JWT-based RLS)       |

---

## Architecture Overview

The project follows a **layered architecture** with strict separation of concerns:

```
API Request → Router → Service → Repository → Supabase
                          ↓
                    Orchestrators
                     ↓        ↓
               LLM Agents   Publishers
```

### Layer Responsibilities

| Layer            | Role                                                                 |
|------------------|----------------------------------------------------------------------|
| **Routers**      | Handle HTTP endpoints, input validation, dependency injection        |
| **Services**     | Business logic, orchestration, no direct DB access                   |
| **Repositories** | Data access layer, all Supabase queries live here                    |
| **Schemas**      | Pydantic models for request/response validation and serialization    |
| **Config**       | Environment variables, DB connections, external client setup         |

---

## Project Structure

```
backend/
├── app/
│   ├── main.py                  # FastAPI app entry point, router registration
│   ├── worker.py                # Background job consumer (PGMQ polling loop)
│   └── dependencies.py          # Dependency injection factory (repos, services, orchestrators)
│
├── config/
│   ├── settings.py              # Env vars, constants (queue name, LLM model, dimensions)
│   └── connections.py           # Supabase admin client, user-scoped client, Groq client
│
├── routers/
│   ├── auth_router.py           # Login / Register endpoints
│   ├── posts_router.py          # CRUD for raw posts
│   ├── upload_router.py         # Image upload to Supabase Storage
│   ├── scrapping_router.py      # URL scraping requests
│   ├── generation_router.py     # Enqueue variant generation jobs (single + batch)
│   ├── variant_router.py        # Variant CRUD, status updates
│   └── publish_router.py        # Trigger publication (single + batch)
│
├── schemas/
│   ├── posts_schemas.py         # RawPostCreate, RawPostResponse
│   ├── variant_schemas.py       # SocialPlatform enum, VariantStatus, Generate/Batch schemas
│   ├── publish_history_schemas.py  # Publish trigger, batch, history CRUD schemas
│   ├── publisher_schemas.py     # PublisherResponse (success, status_code, external_post_id)
│   ├── scraping_schemas.py      # ScrapingRequestCreate, ScrapingStatus
│   ├── upload_schemas.py        # Upload schemas
│   ├── login.py                 # Login schema
│   └── register.py              # Register schema
│
├── repositories/
│   ├── raw_post_repository.py   # raw_posts table CRUD
│   ├── variant_repository.py    # variants table CRUD (create_one, create_many, status updates)
│   ├── publish_history_repository.py  # publish_history table CRUD
│   ├── scraping_repository.py   # scraping_requests table CRUD + status updates
│   └── storage_repository.py    # Supabase Storage bucket operations
│
├── services/
│   ├── scraping_service.py      # URL scraping pipeline (fetch HTML, extract text + og:image)
│   ├── upload_service.py        # Image validation + upload delegation
│   ├── image_processor.py       # Download, resize/crop, re-upload processed images
│   ├── llm_service.py           # Agent discovery, instantiation via @register_agent decorator
│   ├── publish_service.py       # Publisher discovery via @register_publisher, publish dispatch
│   ├── variant_generation_orchestrator.py   # Full generation pipeline orchestrator
│   ├── variant_publishing_orchestrator.py   # Full publishing pipeline orchestrator
│   │
│   ├── agents/                  # LLM Agents (one per platform)
│   │   ├── base_agent.py        # Abstract base: build_prompt(), validate(), generate_variant()
│   │   ├── registry.py          # @register_agent decorator + get_registered_agents()
│   │   ├── linkedin_agent.py    # LinkedIn-specific prompt + validation rules
│   │   ├── facebook_agent.py
│   │   ├── discord_agent.py
│   │   └── telegram_agent.py
│   │
│   └── publishers/              # Social Publishers (one per platform)
│       ├── social_publisher.py  # Abstract base: publish(content, metadata, image_url)
│       ├── registry.py          # @register_publisher decorator + get_registered_publishers()
│       ├── discord_publisher.py # Discord Webhook integration
│       ├── linkedin_publisher.py
│       └── facebook_publisher.py
│
├── tests/
│   ├── conftest.py
│   └── unit/
│
supabase/
└── migrations/                  # SQL migrations (ordered)
    ├── 01_create_raw_posts.sql
    ├── 02_setup_pqmq.sql        # PGMQ extension + background_jobs queue + RPC wrappers
    ├── 03_create_variants.sql
    ├── 04_supabase_bucket.sql
    ├── 05_variants_policies.sql
    ├── 06_enqueue_regeneration_job.sql
    ├── 07_setup_scraping_job.sql     # scraping_requests table + trigger → PGMQ
    ├── 08_create_publish_history.sql  # publish_history table + RLS policies
    ├── 09_setup_publishing_job.sql    # trigger on INSERT → enqueue variant.publish
    ├── 10_atler_type.sql
    └── 11_scheduled_variants.sql
```

---

## How the Worker Works

The worker (`app/worker.py`) is an **independent Python process** that runs alongside the FastAPI server. It continuously polls a single PGMQ queue called `background_jobs`.

### Polling Loop

```
while True:
    1. Call pgmq_read() to fetch 1 message
    2. Extract event type from message payload
    3. Route to the matching handler
    4. On success → pgmq_delete() the message
    5. On failure → message stays in queue (visibility timeout = 60s)
    6. If read_count > MAX_RETRIES (3) → drop the message
    7. Sleep 2 seconds and repeat
```

### Event Routing

The worker uses a simple **event dispatch map** to route jobs:

```python
EVENT_HANDLERS = {
    "variant.generate":   handle_variant_generation,   # → VariantGenerationOrchestrator
    "scraping.requested": handle_scraping_requested,   # → ScrapingService
    "variant.publish":    handle_variant_publish,       # → VariantPublishingOrchestrator
}
```

Each event type maps to a handler function that delegates to the right orchestrator or service.

### How Jobs Enter the Queue

Jobs are enqueued in two ways depending on the use case:

1. **Via Supabase RPC** (variant generation): The API router calls `enqueue_variant_job()` SQL function directly.
2. **Via PostgreSQL Triggers** (scraping + publishing): Inserting a row into `scraping_requests` or `publish_history` automatically fires a trigger that sends a message to PGMQ.

This means the worker does not need to know how jobs arrive — it just reads and processes them.

---

## The Two Orchestrators

### 1. VariantGenerationOrchestrator

Handles the full pipeline for transforming a raw post into a platform-specific variant:

```
Job payload: { post_id, platform }
         │
         ▼
1. Check if a variant already exists for this post+platform
   - If draft/approved/published → skip (idempotent)
   - If rejected → retry with the previous error as feedback
         │
         ▼
2. Fetch the raw post content from RawPostRepository
         │
         ▼
3. Call LLMService.generate_variant_for_platform()
   - Finds the matching @register_agent for the platform
   - Runs LLM generation with retry loop (up to 2 retries on validation failure)
         │
         ▼
4. Persist the generated variant via VariantRepository.create_one()
   - Uses UPSERT on (post_id, platform) constraint
   - Status = DRAFT if valid, REJECTED if validation failed
```

### 2. VariantPublishingOrchestrator

Handles the complete publication workflow for an approved variant:

```
Job payload: { history_id, variant_id }
         │
         ▼
1. Fetch the variant from DB and verify status (must be APPROVED or SCHEDULED)
         │
         ▼
2. Fetch the original post's image URL from RawPostRepository
         │
         ▼
3. Call PublishService.publish_variant()
   - Finds the matching @register_publisher for the platform
   - Executes the platform-specific publish() method (e.g., Discord webhook POST)
         │
         ▼
4. Update publish_history status → "success" + store response payload
         │
         ▼
5. Update variant status → PUBLISHED
```

On failure at any step, the history record is updated to `"failed"` with the error message and the exception is re-raised so PGMQ can retry.

---

## Key Design Patterns

### Decorator-Based Registration (Agents & Publishers)

Both LLM agents and social publishers use a **decorator pattern** for auto-registration. This means adding a new platform is as simple as creating a new file with the decorator — no need to modify any existing code.

**Agents:**
```python
@register_agent
class LinkedInAgent(BaseAgent):
    def build_prompt(self, source_text: str) -> str: ...
    def validate(self, content: str) -> tuple[bool, str | None]: ...
```

**Publishers:**
```python
@register_publisher
class DiscordPublisher(SocialPublisher):
    async def publish(self, content, metadata, image_url) -> PublisherResponse: ...
```

At startup, `LLMService` and `PublishService` dynamically scan their respective directories, import all modules (which triggers the decorators), and build a registry of available agents/publishers. No hardcoded lists, no switch statements.

### Independent Jobs per Platform

When a user requests variant generation for a post, **one independent job is created per platform**. Each job is a separate PGMQ message processed independently by the worker. This gives:

- **Fault isolation**: If LinkedIn generation fails, Twitter and Discord still succeed
- **Independent retries**: Each platform job has its own retry counter
- **Scalability**: Jobs can be processed in parallel with multiple workers

### Database-Driven Job Queuing via Triggers

The scraping and publishing pipelines use **PostgreSQL triggers** to automatically enqueue jobs when a record is inserted. For example:

```sql
CREATE TRIGGER trigger_enqueue_publish
    AFTER INSERT ON public.publish_history
    FOR EACH ROW
    EXECUTE FUNCTION enqueue_publish_job();
```

This is a simple and reliable way to guarantee that every insert results in a background job, with no extra application code needed.

### Row-Level Security (RLS)

Every table uses Supabase RLS policies so users can only access their own data. The worker bypasses RLS using the `service_role` admin client, while API endpoints use user-scoped clients with the JWT token.

### Validation Loop with LLM Feedback

Each agent has a deterministic `validate()` method that checks platform-specific rules (character limits, hashtag counts, forbidden placeholders...). If validation fails, the agent automatically retries by feeding the error back into the conversation history:

```
Attempt 1 → Generate → Validate → FAIL ("too few hashtags")
Attempt 2 → Generate (with error context) → Validate → PASS ✓
```

Up to 2 retries before the variant is saved with status `REJECTED` + the validation error stored for later manual review or regeneration.

---

## Database Schema

```
raw_posts (user content source)
  ├── id, user_id, title, raw_content, image_url
  │
  └──► variants (one per post × platform)
        ├── id, post_id, platform, content, status, error_message, metadata
        │
        └──► publish_history (publication tracking)
              ├── id, variant_id, idempotency_key, status, response_payload
              └── error_message, attempt_count, executed_at

scraping_requests (URL scraping job tracking)
  ├── id, user_id, url, status, error_message
```

### Key Constraints

- `variants(post_id, platform)` is **UNIQUE** — one variant per post per platform
- `publish_history(variant_id)` is **UNIQUE** — one publish attempt per variant
- `publish_history(idempotency_key)` is **UNIQUE** — prevents duplicate publications

---

## API Endpoints

### Raw Posts
| Method | Endpoint               | Description                    |
|--------|------------------------|--------------------------------|
| POST   | `/raw-posts/new`       | Create a raw post              |
| GET    | `/raw-posts/all`       | List all raw posts (paginated) |
| GET    | `/raw-posts/{post_id}` | Get a raw post by ID           |

### Scraping
| Method | Endpoint         | Description                               |
|--------|------------------|-------------------------------------------|
| POST   | `/scraping/url`  | Submit a URL for scraping (trigger → PGMQ)|

### Generation
| Method | Endpoint                | Description                             |
|--------|-------------------------|-----------------------------------------|
| POST   | `/posts/generate`       | Enqueue generation for 1 platform       |
| POST   | `/posts/generate-batch` | Enqueue generation for multiple platforms|

### Variants
| Method | Endpoint                          | Description                        |
|--------|-----------------------------------|------------------------------------|
| GET    | `/variants/post/{post_id}`        | Get all variants for a post        |
| PATCH  | `/variants/{variant_id}/status`   | Update variant status              |

### Publishing
| Method | Endpoint                 | Description                                   |
|--------|--------------------------|-----------------------------------------------|
| POST   | `/publish/trigger`       | Trigger publication for 1 variant              |
| POST   | `/publish/trigger-batch` | Trigger publication for all variants of a post |

### Upload
| Method | Endpoint   | Description                 |
|--------|------------|-----------------------------|
| POST   | `/upload`  | Upload image to storage     |

---

## How to Run

### 1. Setup Environment

```bash
cd backend
cp .env.example .env
# Fill in SUPABASE_URL, SUPABASE_ANON_KEY, SUPABASE_SERVICE_KEY, GROQ_API_KEY
```

### 2. Install Dependencies

```bash
uv sync
```

### 3. Run the API Server

```bash
uv run uvicorn app.main:app --reload
```

### 4. Run the Worker (separate terminal)

```bash
uv run python -m app.worker
```

### 5. Run Tests

```bash
uv run pytest
```
