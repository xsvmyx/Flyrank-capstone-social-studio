# Validation & Constraint Enforcement Evidence

This document provides technical evidence demonstrating that social media post generation constraints (length, tone rules, meta-text placeholders, hashtag counts, and paragraph structure) are strictly enforced in code, and that non-compliant variants are deterministically blocked.

---

## 1. Constraint Profiles Matrix

Platform constraint rules are implemented in agent classes inheriting from `BaseAgent` (`LinkedInAgent`, `FacebookAgent`, etc.):

| Constraint Type | LinkedIn Agent Rules | Facebook Agent Rules | Code Implementation |
| :--- | :--- | :--- | :--- |
| **Character Length** | Min: 30 \| Max: 3000 | Min: 30 \| Max: 2000 | `MIN_LENGTH`, `MAX_LENGTH` |
| **Hashtag Count** | Min: 1 \| Max: 10 | Min: 0 \| Max: 5 | `MIN_HASHTAGS`, `MAX_HASHTAGS` |
| **Forbidden Meta-text** | Blocked | Blocked | `FORBIDDEN_PLACEHOLDERS` |
| **Wall-of-Text Rule** | > 300 chars requires line breaks | > 300 chars requires line breaks | `len(lines) < 2 if length > 300` |

### Forbidden Meta-text & Placeholders
The deterministic validator scans case-insensitively for AI artifacts and prompt leaks:
- `"[insert"`, `"[votre nom]"`, `"[lien]"`, `"[link]"`
- `"as an ai"`, `"here is your post"`

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
```text
============================= test session starts ==============================
platform linux -- Python 3.12.3, pytest-9.1.1
rootdir: /home/samy/Desktop/FlyRank/capstone/backend
configfile: pyproject.toml
plugins: asyncio-1.4.0, mock-3.15.1
collected 16 items

tests/unit/test_agent_constraints.py::test_empty_content_blocked PASSED                          [  6%]
tests/unit/test_agent_constraints.py::test_linkedin_blocked_when_too_short PASSED              [ 12%]
tests/unit/test_agent_constraints.py::test_linkedin_blocked_when_29_chars_boundary PASSED      [ 18%]
tests/unit/test_agent_constraints.py::test_linkedin_passed_exact_30_chars_boundary PASSED      [ 25%]
tests/unit/test_agent_constraints.py::test_linkedin_blocked_when_too_long PASSED               [ 31%]
tests/unit/test_agent_constraints.py::test_facebook_blocked_when_exceeds_2000_chars PASSED    [ 37%]
tests/unit/test_agent_constraints.py::test_linkedin_blocked_when_ai_placeholder_present PASSED [ 43%]
tests/unit/test_agent_constraints.py::test_facebook_blocked_when_bracket_placeholder_present PASSED [ 50%]
tests/unit/test_agent_constraints.py::test_case_insensitive_forbidden_placeholders PASSED      [ 56%]
tests/unit/test_agent_constraints.py::test_linkedin_blocked_when_no_hashtags PASSED             [ 62%]
tests/unit/test_agent_constraints.py::test_linkedin_blocked_when_too_many_hashtags PASSED       [ 68%]
tests/unit/test_agent_constraints.py::test_facebook_blocked_when_too_many_hashtags PASSED       [ 75%]
tests/unit/test_agent_constraints.py::test_single_paragraph_too_long_blocked PASSED             [ 81%]
tests/unit/test_agent_constraints.py::test_multiple_simultaneous_violations_accumulated PASSED [ 87%]
tests/unit/test_agent_constraints.py::test_linkedin_valid_variant_passed PASSED                 [ 93%]
tests/unit/test_agent_constraints.py::test_facebook_valid_variant_passed PASSED                 [100%]

============================== 16 passed in 0.12s ==============================
```

---

## 4. Complete Test Suite Execution

### Command Executed
```bash
cd backend
uv run pytest
```

### Summary Output
```text
============================================== test session starts ===============================================
platform linux -- Python 3.12.13, pytest-9.1.1, pluggy-1.6.0
rootdir: /home/samy/Desktop/FlyRank/capstone/backend
configfile: pyproject.toml
plugins: mock-3.15.1, asyncio-1.4.0, anyio-4.15.1
asyncio: mode=Mode.AUTO, debug=False, asyncio_default_fixture_loop_scope=None, asyncio_default_test_loop_scope=function
collected 57 items                                                                                               

tests/unit/test_agent_constraints.py ................                                                      [ 28%]
tests/unit/test_llm_service.py ........                                                                    [ 42%]
tests/unit/test_scraping_service.py .............                                                          [ 64%]
tests/unit/test_upload_service.py .......                                                                  [ 77%]
tests/unit/test_variant_generation_orchestrator.py .............                                           [100%]

=============================================== 57 passed in 0.26s  ===============================================
```
