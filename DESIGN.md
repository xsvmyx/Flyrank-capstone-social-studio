# Design Document: Social Media Studio

## 1. Problem Statement
Content creators and marketing teams often spend significant manual effort repurposing long-form content (blog posts, articles, documentation) into platform-specific social media posts. Each social platform imposes distinct technical constraints (character limits, hashtag density, tone, formatting) and publication protocols. 

**Social Media Studio** provides an automated, reliable system to ingest long-form content, generate constrained platform-tailored post variants, support human-in-the-loop editorial review, and publish idempotently across social networks on durable schedules.

---

## 2. Data Model

The data layer is hosted on PostgreSQL (via Supabase) and structured around four core entities and a durable message queue:

1. **`raw_posts` (Ingested Content)**
   - `id` (UUID, PK)
   - `user_id` (UUID, FK auth.users)
   - `source_url` (text, nullable)
   - `original_text` (text, required)
   - `created_at` / `updated_at` (timestamptz)

2. **`variants` (Platform Posts & Review Workflow)**
   - `id` (UUID, PK)
   - `post_id` (UUID, FK raw_posts)
   - `platform` (enum: `linkedin`, `facebook`, `discord`, `telegram`)
   - `content` (text, non-empty, strictly validated)
   - `status` (enum: `draft`, `approved`, `rejected`, `scheduled`, `published`, `failed`)
   - `scheduled_at` (timestamptz, nullable slot for future publishing)
   - `error_message` (text, nullable, records rule violation reasons)
   - `metadata` (jsonb, token counts, model metadata, images)

3. **`publish_history` (Publish Attempts & Audit Trail)**
   - `id` (UUID, PK)
   - `variant_id` (UUID, FK variants)
   - `idempotency_key` (text, UNIQUE, format: `{variant_id}_{timestamp_or_slot}`)
   - `status` (enum: `queued`, `success`, `failed`, `skipped`)
   - `attempt_count` (int, default 1)
   - `response_payload` (jsonb, external API payload or mock ID)
   - `error_message` (text, nullable)
   - `executed_at` (timestamptz)

4. **Durable Queue (`pgmq.background_jobs`)**
   - Managed background jobs (`variant.generate`, `variant.publish`, `scraping.fetch`)
   - Enforces persistent delivery, retry visibility timeouts, and worker crash safety.

---

## 3. SocialPublisher Interface & Adapter Layer

All platform destinations conform to the `SocialPublisher` abstract interface:

```python
class SocialPublisher(ABC):
    platform_name: str

    @abstractmethod
    async def publish(
        self,
        content: str,
        metadata: Optional[dict] = None,
        image_url: Optional[str] = None
    ) -> PublisherResponse:
        """Publishes content and returns standardized PublisherResponse."""
        pass
```

- **Registered Adapters:**
  - `DiscordPublisher` (*Real free platform*): Dispatches to Discord channels via Webhooks.
  - `LinkedInPublisher` (*Mock adapter*): Simulates LinkedIn REST API execution with mock external IDs.
  - `FacebookPublisher` (*Mock adapter*): Simulates Meta Graph API execution.
- **Pluggability:** Adapters register via `@register_publisher`. Swapping an adapter requires configuring settings/keys without changing any business orchestration code.

---

## 4. API Surface

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `POST` | `/raw-posts/new` | Ingest pasted Markdown or raw text into `raw_posts` |
| `POST` | `/scrapping/` | Fetch blog article via URL, extract text + metadata, enqueue ingestion |
| `POST` | `/generate/batch` | Trigger variant generation for stored post across specified platforms |
| `GET` | `/variants/post/{post_id}` | Retrieve generated variants for a post |
| `PATCH`| `/variants/{variant_id}/status` | Review workflow: approve, reject, or schedule a variant |
| `POST` | `/publish/trigger` | Trigger immediate publication of an approved variant |
| `POST` | `/publish/trigger-batch` | Trigger publication for all approved variants of a post |
| `GET` | `/publish/history/{variant_id}` | Retrieve attempt history & results for a specific variant |
| `GET` | `/publish/history` | Retrieve paginated publish attempts and outcomes |

---

## 5. Explicit Non-Goals

1. **Non-Goal: Full-Fledged Frontend CMS & Rich-Text WYSIWYG Editor.**  
   The system intentionally exposes a clean REST API and async worker pipeline. While a lightweight client or API docs (Swagger/OpenAPI) can interact with it, building an interactive multi-tenant drag-and-drop web dashboard with live post preview rendering is out of scope for this backend engine.

2. **Non-Goal: Real Paid Platform Integrations Requiring Complex OAuth2 User Grants.**  
   Platforms like LinkedIn and Meta require paid partner verification, developer app review, and complex multi-step OAuth redirects for end-users. The system uses a real free webhook adapter (Discord) to prove end-to-end network delivery, and mock adapters for enterprise networks to prove architectural neutrality.
