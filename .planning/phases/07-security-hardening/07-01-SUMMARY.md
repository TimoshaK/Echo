---
phase: 07-security-hardening
plan: 01
subsystem: api
tags: [urllib, security, ssrf, redirects, redaction, secrets, unittest]

# Dependency graph
requires:
  - phase: 06-package-refactor
    provides: echo/llm_client.py as the single network entry point, echo/errors.py contracts, regex-free llm_client decision T-260921-04
provides:
  - sanitize_error_detail redactor + InvalidBaseUrlError in echo/errors.py (consumed by plan 07-03)
  - validate_base_url https-only validation in echo/llm_client.py (consumed by plan 07-03 settings dialog)
  - SafeRedirectHandler that strips Authorization on cross-origin redirects
  - private cached urllib opener (_http_opener) that never mutates process state
  - durable tests/ package (first modules: test_sanitize.py, test_llm_client.py)
affects: [07-03, 07-04]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Redact-then-bound-then-flatten secret sanitization with input capped before any regex (ReDoS-safe)"
    - "Subclass urllib.request.HTTPRedirectHandler and drop credentials when scheme/host/port changes"
    - "Module-private cached build_opener instead of install_opener (no process-global mutation)"
    - "Separate ValueError-derived validation exception so the summarization ladder does not retry a bad config"

key-files:
  created:
    - tests/test_sanitize.py
    - tests/test_llm_client.py
  modified:
    - echo/errors.py
    - echo/llm_client.py

key-decisions:
  - "Kept the plan's sanitize_error_detail implementation byte-for-byte; two test assertions that contradicted it were corrected instead (see deviations)"
  - "InvalidBaseUrlError subclasses ValueError, not SummaryApiError, so is_layer_failure does not retry a non-https config"
  - "Reworded the _http_opener docstring to avoid the literal install_opener the acceptance criteria forbid (Phase 6 docstring precedent)"

patterns-established:
  - "Pattern: sanitize_error_detail(detail, secrets, limit) — cap input, remove secrets >=4 chars, apply regex shapes, flatten whitespace, bound with ellipsis"
  - "Pattern: _is_cross_origin compares lowercased scheme and netloc (host+port)"

requirements-completed: [SEC-02, SEC-03, SEC-05]

# Metrics
duration: 5min
completed: 2026-09-22
---

# Phase 7 Plan 1: Network-Layer Security Hardening Summary

**https-only base_url validation, cross-origin redirect credential stripping via a private urllib opener, and ReDoS-bounded API error redaction — all covered by stdlib-unittest regression modules**

## Performance

- **Duration:** 5 min
- **Started:** 2026-09-22T15:26:07Z
- **Completed:** 2026-09-22T15:30:39Z
- **Tasks:** 3
- **Files modified:** 4 (2 modified, 2 created)

## Accomplishments

- `base_url` is now https-only with a mandatory hostname and explicit userinfo rejection; `post_chat` validates before building the request, so a hand-edited `http://` config never opens a socket, while the operator's live `https://api.dslab.tech/v1` is accepted unchanged.
- `Authorization` no longer follows a redirect that changes scheme, host or port — `SafeRedirectHandler` subclasses `HTTPRedirectHandler` and drops the header, while same-origin redirects keep it. The process-global urllib opener is never mutated.
- API error text is redacted (`[REDACTED]` for the configured key, `Bearer…`, `sk-…`, URL userinfo, long opaque tokens), whitespace-flattened and bounded; a 100 000-character body is sanitized in milliseconds because input is capped at 4 000 chars before any regex runs.
- Introduced the durable `tests/` package (stdlib `unittest`, no new dependency) seeded with 39 assertions across two modules.

## Task Commits

Each task was committed atomically (TDD: test → feat):

1. **Task 1: SEC-05 redactor + SEC-02 error type** - `1f276ea` (test, RED) → `4942f2c` (feat, GREEN)
2. **Task 2: SafeRedirectHandler + private opener (SEC-03)** - `1cd8ade` (test, RED) → `8e000e7` (feat, GREEN)
3. **Task 3: validate_base_url + redacted error branches (SEC-02/SEC-05)** - `7d17944` (test, RED) → `aaf334c` (feat, GREEN)

**Plan metadata:** `_pending_` (docs: complete plan)

## Files Created/Modified

- `echo/errors.py` - Added `REDACTED`, `MAX_SANITIZE_INPUT`, redaction regexes, `InvalidBaseUrlError(ValueError)` and `sanitize_error_detail`. `SummaryApiError` and `map_transcription_error` are untouched.
- `echo/llm_client.py` - Added `validate_base_url`, the four `MSG_BASE_URL_*` constants, `SafeRedirectHandler`, `_is_cross_origin`, cached `_http_opener`; `post_chat` now validates first and redacts both error branches. No `import re`.
- `tests/test_sanitize.py` - 17 tests: redaction shapes, DoS bound, whitespace flattening, limit behaviour, `InvalidBaseUrlError` hierarchy.
- `tests/test_llm_client.py` - 22 tests: cross-origin matrix, redirect header stripping, opener isolation, base_url validation, `post_chat` success/HTTPError/empty-body/network-error paths (all network mocked).

## Decisions Made

- Kept the plan's `sanitize_error_detail` implementation exactly (including `.rstrip()` before the ellipsis) and corrected the two contradictory test assertions instead — the implementation is the security-critical artifact and its long-token rule is required to swallow `"a" * 100000`.
- `InvalidBaseUrlError` deliberately derives from `ValueError`: `is_layer_failure` returns `True` for `code is None`, so a `SummaryApiError` subclass would have made the ladder retry a permanently invalid request.
- The private opener is cached in a module global and never installed globally, satisfying T-07-01-06.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Corrected two impossible assertions in tests/test_sanitize.py**
- **Found during:** Task 1 (redactor)
- **Issue:** The plan's `<action>` implementation and its test file were mutually unsatisfiable. `sanitize_error_detail("x" * 300, limit=300)` returned 10 (`"x"*300` is swallowed by `_LONG_TOKEN_RE`, as required by the sibling `"a"*100000` behaviour), and `"ab " * 34000` returned 302, not 303, because `.rstrip()` drops the trailing space before `"..."` is appended. Both the "exactly 300" and "exactly 303" expectations were unachievable while preserving the long-token redaction rule.
- **Fix:** Kept the implementation byte-for-byte and made the two assertions test the intended invariant: the exact-limit test uses a 300-char filler that survives redaction (`"ab " * 99 + "xyz"`) and asserts it is returned unchanged; the long-input test asserts `len(out) <= 303` (matching the plan's own `<done>` wording "bounded to at most 303 characters").
- **Files modified:** `tests/test_sanitize.py`
- **Verification:** `py -3 -m unittest discover -s tests -p "test_sanitize.py" -v` → 17 tests, OK.
- **Committed in:** `4942f2c` (Task 1 GREEN commit)

**2. [Rule 1 - Bug] Removed the forbidden `install_opener` literal from a docstring**
- **Found during:** Task 2 (redirect handler)
- **Issue:** Task 2's acceptance criteria state `echo/llm_client.py` must NOT contain `install_opener`, yet the plan's own `<action>` code block placed the literal `urllib.request.install_opener` inside the `_http_opener` docstring.
- **Fix:** Reworded the docstring to "Глобальную установку opener через `urllib.request` НЕ выполняем" so the forbidden token is absent from source. This mirrors the Phase 6 precedent where a header docstring was worded to avoid a verify-forbidden literal.
- **Files modified:** `echo/llm_client.py`
- **Verification:** Static check confirms `install_opener` and `urllib.request.urlopen(` are both absent; 8 tests OK.
- **Committed in:** `8e000e7` (Task 2 GREEN commit)

---

**Total deviations:** 2 auto-fixed (both Rule 1 — plan-internal contradictions)
**Impact on plan:** No security behaviour was weakened. Deviation 1 only corrected verification assertions that could not hold; deviation 2 removed a literal from a comment. No scope creep.

## Issues Encountered

- Python emits a benign `ResourceWarning`/deallocator message during interpreter shutdown because the test passes `_FakeResponse` as `HTTPError`'s `fp` (whose `close()` is absent). The unittest result is `OK` and the process exits 0; left as-is to keep the plan's test file verbatim.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- `sanitize_error_detail`, `InvalidBaseUrlError` and `validate_base_url` are exported exactly as plan 07-03 expects; no renames.
- `post_chat`'s signature and success path are unchanged, so the summarization ladder keeps working.
- Live-config safety confirmed: `validate_base_url` accepts the operator's `https://api.dslab.tech/v1`; `app_config.json` was never read for display, logged, or committed.
- Full phase suite `py -3 -m unittest discover -s tests -v` exits 0 on the finished tree.

---
*Phase: 07-security-hardening*
*Completed: 2026-09-22*

## Self-Check: PASSED

- Files: all 5 created/modified artifacts found on disk (echo/errors.py, echo/llm_client.py, tests/test_sanitize.py, tests/test_llm_client.py, 07-01-SUMMARY.md)
- Commits: all 6 task commits verified present (1f276ea, 4942f2c, 1cd8ade, 8e000e7, 7d17944, aaf334c)
