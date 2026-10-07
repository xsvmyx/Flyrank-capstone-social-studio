# Validation & Constraint Enforcement Evidence

This document provides technical evidence demonstrating that social media post generation constraints (length, tone rules, meta-text placeholders, hashtag counts, and paragraph structure) are strictly enforced in code, and that non-compliant variants are deterministically blocked.

---

## 1. Constraint Profiles Matrix

Platform constraint rules are implemented in agent classes inheriting from `BaseAgent` (`LinkedInAgent`, `FacebookAgent`, `DiscordAgent`):

| Constraint Type | LinkedIn | Facebook | Discord | Code Implementation |
| :--- | :--- | :--- | :--- | :--- |
| **Min Length** | 30 chars | 30 chars | 10 chars | `MIN_LENGTH` |
| **Max Length** | 3 000 chars | 2 000 chars | 2 000 chars | `MAX_LENGTH` |
| **Min Hashtags** | 1 | 0 | 0 (social hashtags banned) | `MIN_HASHTAGS` |
| **Max Hashtags** | 10 | 5 | 4 soft cap (channel refs OK) | `MAX_HASHTAGS` |
| **Forbidden Meta-text** | Blocked | Blocked | Blocked (regex) | `FORBIDDEN_PLACEHOLDERS` / `FORBIDDEN_PATTERNS` |
| **Wall-of-Text Rule** | > 300 chars → line breaks required | > 300 chars → line breaks required | > 400 chars → line breaks required | `len(lines) < 2` |
| **Tone** | Professional / conversational | Warm / community | Casual / Discord Markdown | Prompt guidelines |

### Forbidden Meta-text & Placeholders
The deterministic validator scans case-insensitively for AI artifacts and prompt leaks:
- `"[insert"`, `"[your name]"`, `"[lien]"`, `"[link]"`
- `"as an ai"`, `"here is your post"`
- Discord uses compiled regex patterns to catch all variants of the above.

---

## 2. Validation Mechanism & Retry Pipeline

1. **Generation / Regeneration**: An LLM agent generates a raw text response.
2. **Deterministic Check (`agent.validate`)**:
   - Compiles all violations into a list of error strings.
   - If any violation exists, returns `(False, "error1 | error2")`.
3. **Blocking & Automatic Retry**:
   - If `is_valid == False`, `BaseAgent` logs the failure and automatically triggers a correction prompt to Groq (up to `MAX_RETRIES = 2`).
   - If validation continues to fail, the variant is flagged with `is_valid = False` and the validation error message is stored in DB.

---

## 3. Test Transcript & Execution Proof

### Command Executed
```bash
cd backend
uv run pytest tests/unit/test_agent_constraints.py -v
```

### Terminal Output
```bash
~/Desktop/FlyRank/capstone/backend main*
backend ❯ pytest tests/unit/test_agent_constraints.py
============================================== test session starts ===============================================
platform linux -- Python 3.12.13, pytest-9.1.1, pluggy-1.6.0
rootdir: /home/samy/Desktop/FlyRank/capstone/backend
configfile: pyproject.toml
plugins: mock-3.15.1, asyncio-1.4.0, anyio-4.15.1
asyncio: mode=Mode.AUTO, debug=False, asyncio_default_fixture_loop_scope=None, asyncio_default_test_loop_scope=function
collected 16 items                                                                                               

tests/unit/test_agent_constraints.py ................                                                      [100%]

=============================================== 16 passed in 0.08s ===============================================
```

---

## 4. Complete Test Suite Execution

### Command Executed
```bash
~/Desktop/FlyRank/capstone/backend main*
backend ❯ pytest
============================================== test session starts ===============================================
platform linux -- Python 3.12.13, pytest-9.1.1, pluggy-1.6.0
rootdir: /home/samy/Desktop/FlyRank/capstone/backend
configfile: pyproject.toml
plugins: mock-3.15.1, asyncio-1.4.0, anyio-4.15.1
asyncio: mode=Mode.AUTO, debug=False, asyncio_default_fixture_loop_scope=None, asyncio_default_test_loop_scope=function
collected 76 items                                                                                               

tests/unit/test_agent_constraints.py ................                                                      [ 21%]
tests/unit/test_llm_service.py .....                                                                       [ 27%]
tests/unit/test_publish_service.py .........                                                               [ 39%]
tests/unit/test_publishers.py .......                                                                      [ 48%]
tests/unit/test_scraping_service.py .............                                                          [ 65%]
tests/unit/test_upload_service.py .......                                                                  [ 75%]
tests/unit/test_variant_generation_orchestrator.py ...........                                             [ 89%]
tests/unit/test_variant_publishing_orchestrator.py ........                                                [100%]

=============================================== 76 passed in 1.35s ===============================================
```


## 5. Adapter Layer Evidence (SocialPublisher Interface)

**Requirement:** "Adapter layer: one SocialPublisher interface, one real free platform, and at least two mock adapters. An adapter swap changes configuration, not business logic."

### Architecture Proof
Our project uses a `@register_publisher` decorator pattern. The business logic (`PublishService` and `VariantPublishingOrchestrator`) never hardcodes platform logic. They rely on the `SocialPublisher` base interface.

We have:
- **Base Interface:** `SocialPublisher` (`backend/services/publishers/social_publisher.py`)
- **Real Platform:** Discord Webhook Adapter (`backend/services/publishers/discord_publisher.py`)
- **Mock Adapters:** LinkedIn & Facebook (which simulate API calls and return mock IDs).

### Execution Proof (Adapter Swap)

**Command Executed:**
```bash
# Single batch call: triggers Discord (real webhook) AND LinkedIn (mock adapter) simultaneously
curl -s -w "\nHTTP_STATUS: %{http_code}" -X POST http://localhost:8000/publish/trigger-batch \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <JWT>" \
  -d '{"post_id": "de4e6e91-c0c6-4e16-b40d-2fd19347b46d", "platforms": ["discord", "linkedin"]}'
```

**Terminal Output:**
```json
{
  "message": "Batch publish completed: 2/2 job(s) queued.",
  "post_id": "de4e6e91-c0c6-4e16-b40d-2fd19347b46d",
  "results": [
    {
      "variant_id": "ce0f1dea-63db-4f8f-99b6-bf6af8770e04",
      "platform": "discord",
      "status": "queued",
      "message": "Publication request queued successfully."
    },
    {
      "variant_id": "d4dad170-bb3c-41ae-814f-3d90fc1baf4e",
      "platform": "linkedin",
      "status": "queued",
      "message": "Publication request queued successfully."
    }
  ]
}
HTTP_STATUS: 202
```
> Both adapters (Discord real webhook + LinkedIn mock) were dispatched from the same business logic call. Swapping an adapter requires no change to `PublishService` or `VariantPublishingOrchestrator`.

---

## 6. Idempotent Publish Evidence

**Requirement:** "Idempotent publish: the same variant and slot never post two times, even under retries."

### Architecture Proof
The `publish_history` table utilizes a `UNIQUE (idempotency_key)` constraint. Furthermore, when `VariantPublishingOrchestrator` processes a job, it strictly checks if the variant's status is already `PUBLISHED` (or if a success record already exists) before attempting the external HTTP request, effectively preventing double posting.

### Execution Proof (Repeated Call Transcript)

**First Attempt** — already executed in Section 5 above (Discord + LinkedIn queued, `HTTP_STATUS: 202`).

**Second Attempt (same post, same platforms):**
```bash
curl -s -w "\nHTTP_STATUS: %{http_code}" -X POST http://localhost:8000/publish/trigger-batch \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <JWT>" \
  -d '{"post_id": "de4e6e91-c0c6-4e16-b40d-2fd19347b46d", "platforms": ["discord", "linkedin"]}'
```

**Terminal Output:**
```json
{
  "detail": {
    "message": "No jobs were queued. All variants were either already published, unapproved, or missing.",
    "post_id": "de4e6e91-c0c6-4e16-b40d-2fd19347b46d",
    "results": [
      {
        "variant_id": "ce0f1dea-63db-4f8f-99b6-bf6af8770e04",
        "platform": "discord",
        "status": "skipped",
        "message": "Variant has already been successfully published."
      },
      {
        "variant_id": "d4dad170-bb3c-41ae-814f-3d90fc1baf4e",
        "platform": "linkedin",
        "status": "skipped",
        "message": "Variant has already been successfully published."
      }
    ]
  }
}
HTTP_STATUS: 400
```
> The second call is immediately rejected. Both variants are flagged `skipped / already published`. The same content can never be sent twice to the same platform.

---

## 7. Review Workflow Evidence

**Requirement:** *"Only approved variants can be scheduled. An unapproved schedule attempt returns a 4xx status code with an error message."*

### Execution Proof (DRAFT variant blocked)

```bash
curl -s -w "\nHTTP_STATUS: %{http_code}" -X POST http://localhost:8000/publish/trigger-batch \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <JWT>" \
  -d '{"post_id": "de4e6e91-c0c6-4e16-b40d-2fd19347b46d", "platforms": ["telegram"]}'
```

**Terminal Output:**
```json
{
  "detail": {
    "message": "No jobs were queued. All variants were either already published, unapproved, or missing.",
    "post_id": "de4e6e91-c0c6-4e16-b40d-2fd19347b46d",
    "results": [
      {
        "variant_id": "3a38d63c-dc9e-44a7-a049-dbf05657d436",
        "platform": "telegram",
        "status": "skipped",
        "message": "Variant cannot be published because its status is 'VariantStatus.DRAFT'. It must be 'approved' or 'scheduled'."
      }
    ]
  }
}
HTTP_STATUS: 400
```
> The Telegram variant has status `DRAFT`. The API immediately rejects the publish attempt with **HTTP 400** and an explicit error message naming the broken rule: the variant must be `approved` or `scheduled`.

---

## 8. Scheduled Publishing & Durable Scheduling Evidence

**Requirement:** *"Durable scheduling: a worker restart mid-batch continues with zero duplicate posts."*

### Architecture Proof
When a variant status is updated to `scheduled`, the API enqueues a delayed message into PGMQ (`background_jobs`) with the delay calculated from `scheduled_at - now`. 
Because jobs are stored durably in PostgreSQL (PGMQ), any worker restart during the delay or processing phase will seamlessly resume jobs without loss or duplicate executions (guaranteed by `publish_history` idempotency constraints).

### Execution Proof (Scheduled Endpoint Transcript)

#### 1. Past Timestamp Check (Rejected with HTTP 400)
```bash
curl -s -w "\nHTTP_STATUS: %{http_code}" -X PATCH http://localhost:8000/variants/13506ccd-62e9-4ea4-81e7-99f55a848ed4/status \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <JWT>" \
  -d '{"status": "scheduled", "scheduled_at": "2026-10-06T15:15:30.000Z"}'
```

**Terminal Output:**
```json
{
  "detail": "'scheduled_at' must be a future timestamp."
}
HTTP_STATUS: 400
```

#### 2. Successful Scheduling (HTTP 200)
```bash
curl -s -w "\nHTTP_STATUS: %{http_code}" -X PATCH http://localhost:8000/variants/13506ccd-62e9-4ea4-81e7-99f55a848ed4/status \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <JWT>" \
  -d '{"status": "scheduled", "scheduled_at": "2026-10-06T15:17:30.000Z"}'
```

**Terminal Output:**
```json
{
  "id": "13506ccd-62e9-4ea4-81e7-99f55a848ed4",
  "post_id": "7dd3d122-8fd5-476e-863f-7f5247bc3d21",
  "platform": "discord",
  "content": "# 👀 Computer Vision in Action\n\n...",
  "status": "scheduled",
  "error_message": null,
  "metadata": {},
  "created_at": "2026-10-06T15:04:18.297914Z",
  "updated_at": "2026-10-06T15:16:17.758404Z"
}
HTTP_STATUS: 200
```
> The variant status is updated to `scheduled` and a delayed job (`variant.publish`) is queued in PGMQ.

#### 3. Attempting to Re-schedule non-APPROVED Variant (HTTP 400)
```bash
curl -s -w "\nHTTP_STATUS: %{http_code}" -X PATCH http://localhost:8000/variants/13506ccd-62e9-4ea4-81e7-99f55a848ed4/status \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <JWT>" \
  -d '{"status": "scheduled", "scheduled_at": "2026-10-06T15:17:30.000Z"}'
```

**Terminal Output:**
```json
{
  "detail": "Cannot schedule a variant that is not currently approved."
}
HTTP_STATUS: 400
```
> Re-scheduling is blocked because the variant is no longer in `APPROVED` status (it's `PUBLISHED`), preventing duplicate queueing.

---

## 9. Publish History Visibility Evidence

**Requirement:** *"Publish history: each attempt is recorded and visible, with its result."*

### Architecture Proof
Every publish attempt (whether immediate or via scheduled background job) creates or updates a record in the `publish_history` table:
- Includes `idempotency_key`, `status` (`pending`, `success`, `failed`), external `response_payload`, `error_message`, `attempt_count`, and `executed_at`.
- Accessible via endpoints `GET /publish/history/{variant_id}` and `GET /publish/history` (with `limit` and `offset` pagination).

### Execution Proof (Querying History Endpoint)

**Command:**
```bash
curl -s -w "\nHTTP_STATUS: %{http_code}" -X GET http://localhost:8000/publish/history/ce0f1dea-63db-4f8f-99b6-bf6af8770e04 \
  -H "Authorization: Bearer <JWT>"
```

**Terminal Output:**
```json
[
  {
    "id": "6d3a8227-7751-4f18-a647-8cfb62e49c71",
    "variant_id": "ce0f1dea-63db-4f8f-99b6-bf6af8770e04",
    "idempotency_key": "ce0f1dea-63db-4f8f-99b6-bf6af8770e04_2026-10-06T15:15:00.000000Z",
    "status": "success",
    "response_payload": {
      "platform": "discord",
      "success": true,
      "status_code": 204,
      "external_post_id": "webhook-delivered"
    },
    "error_message": null,
    "attempt_count": 1,
    "executed_at": "2026-10-06T15:15:02.128451Z",
    "created_at": "2026-10-06T15:15:01.810232Z"
  }
]
HTTP_STATUS: 200
```
> Every attempt is durably recorded in database and directly visible through the API along with status, payload, and timestamps.


