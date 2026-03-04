# Task Proposals from Codebase Review

## 1) Typo Fix Task
**Title:** Fix repository README title capitalization typo.

**Issue found:** The README currently starts with `open ai codex work here`, which should be properly capitalized and branded.

**Proposed change:** Update line 1 to something clear like `OpenAI Codex work here.` (or a more descriptive project title).

**Acceptance criteria:**
- README opening line uses correct capitalization/spelling.
- Wording is intentionally human-readable and project-appropriate.

---

## 2) Bug Fix Task
**Title:** Remove token generation + print side effect during server startup.

**Issue found:** `backend/server.py` imports `create_access_token` and prints a generated internal token at import/startup time. This leaks sensitive auth material into logs and creates unintended runtime side effects.

**Proposed change:** Remove the startup token generation/print lines and keep token creation only in explicit auth flows.

**Acceptance criteria:**
- No token is generated or printed during app import/startup.
- Server logs no longer expose bearer token material.
- Existing authentication flow still works.

---

## 3) Comment/Documentation Discrepancy Task
**Title:** Align GraphQL route comment with the actual mounted path.

**Issue found:** A comment says `Protect BOTH GET + POST on /graphql`, but the router is mounted at `/8124data`.

**Proposed change:** Update the comment to reference `/8124data` (or rename route + related comments consistently if `/graphql` is intended).

**Acceptance criteria:**
- Route comments match actual route configuration.
- No misleading path references remain in this section.

---

## 4) Test Improvement Task
**Title:** Add unit tests for pagination normalization boundary behavior.

**Issue found:** `normalize_pagination` contains important boundary handling (page min clamp, default page size reset, max page size clamp) that is easy to regress without tests.

**Proposed change:** Add tests covering:
- `page` values below 1 clamp to 1.
- `page_size` below 1 resets to default.
- `page_size` above max clamps to max.
- happy-path values pass through unchanged.

**Acceptance criteria:**
- A test module exists for `backend/utils/pagination.py`.
- Tests cover boundary + normal inputs for `normalize_pagination`.
- Test suite passes in CI/local runner.
