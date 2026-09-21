---
phase: 06-refactor-main-into-echo-package
plan: 02
subsystem: refactor
tags: [python, llm-client, transcription-engine, summarization-engine, request-ladder, urllib]

# Dependency graph
requires:
  - phase: 06-refactor-main-into-echo-package (Plan 01)
    provides: "echo.config (load_config/save_config), echo.presets (DEFAULT_PRESET/SUMMARY_PRESETS), echo.errors (SummaryApiError)"
provides:
  - "echo.llm_client: the single network point post_chat(config, payload) + pure helpers json_schema_format, json_instruction, build_messages, parse_json_content, render_sections, try_render, is_layer_failure"
  - "echo.transcription_engine: TranscriptionEngine with lazy whisper base load and status/complete/error queue contract"
  - "echo.summarization_engine: SummarizationEngine driving the json_schema -> json_object -> plain-text ladder"
  - "No-network ladder equivalence proof (harness passes against both echo.summarization_engine and the untouched main baseline)"
affects: [06-03, 06-04, 06-05, 06-06]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Stateless transport/pure-helper module (echo.llm_client) separate from stateful orchestration (echo.summarization_engine)"
    - "Network single point: post_chat is the only urlopen call site in the app"
    - "Engine delegates pure helpers to a module namespace (llm_client.fn) instead of private static methods"
    - "Linear-only JSON extraction (strip + first-{/last-} slice + json.loads), regex explicitly forbidden"

key-files:
  created:
    - echo/llm_client.py
    - echo/transcription_engine.py
    - echo/summarization_engine.py
  modified: []

key-decisions:
  - "llm_client is stateless: config is passed explicitly into post_chat instead of read from self.config"
  - "parse_json_content kept linear-only (no re import); asserted absent so T-260921-04 cannot regress"
  - "is_layer_failure truth table preserved exactly (None/400/422 -> True; 401/403/429/5xx/0 -> False) so terminal errors never retry"
  - "The eight moved helpers are deleted from SummarizationEngine; only _request_content and summarize remain as ladder members"
  - "Preset read from the user-editable config is registry-validated with DEFAULT_PRESET fallback in __init__ (T-260921-01)"

patterns-established:
  - "Single network boundary in a leaf-ish module that only imports json/urllib/echo.errors"
  - "Behavioral equivalence proven by a transient no-network harness run against BOTH the new module and the baseline"

requirements-completed: [REFR-01, REFR-02]

# Metrics
duration: 3min
completed: 2026-09-21
---

# Phase 6 Plan 02: Non-GUI Engine Layer Summary

**Relocated the LLM client and both engines out of `main.py` into `echo/llm_client.py`, `echo/transcription_engine.py` and `echo/summarization_engine.py`, with the `json_schema → json_object → plain-text` ladder proven behaviorally identical to the baseline via a no-network harness.**

## Performance

- **Duration:** ~3 min
- **Started:** 2026-09-21T15:44:26Z
- **Completed:** 2026-09-21T15:47:43Z
- **Tasks:** 3
- **Files modified:** 3 created, 0 modified

## Accomplishments
- `echo/llm_client.py` is now the **only** network point in the app: `post_chat(config, payload)` performs the POST to `/chat/completions` and the API key travels **only** in the `Authorization` header (T-06-01 / T-260921-02), verified by the harness assertion on every recorded request.
- The seven pure helpers (`json_schema_format`, `json_instruction`, `build_messages`, `parse_json_content`, `render_sections`, `try_render`, `is_layer_failure`) moved as stateless module functions with their Russian rationale docstrings intact.
- `echo/transcription_engine.py` carries `TranscriptionEngine` verbatim — lazy `whisper.load_model("base")`, thread-safe `model_lock`, and the `status`/`complete`/`error` queue keys (`text`, `language`, `segments`, `error`) unchanged.
- `echo/summarization_engine.py` owns the mutable state and the ladder. The eight moved helpers no longer exist on the class; `_request_content` and `summarize` are the only ladder members left, delegating to `llm_client.*`.
- The `summarize()` ladder, terminal-error short-circuit and unknown-preset fallback were proven equivalent: `SMOKE_SUMMARIZE_ALL_PASS` printed against **both** `echo.summarization_engine` and the untouched `main` baseline.
- No module in the non-GUI layer imports `tkinter`; `main.py` and `app_config.py` remain untouched, so the baseline app is still green (D-03, D-05).

## Task Commits

Each task was committed atomically:

1. **Task 1: Create echo/llm_client.py with the network call and pure helpers** - `ff536fe` (feat)
2. **Task 2: Create echo/transcription_engine.py** - `80b5507` (feat)
3. **Task 3: Create echo/summarization_engine.py and prove the ladder with a no-network harness** - `b3e6271` (feat)

**Plan metadata:** `docs(06-02): complete non-GUI engine layer plan` (recorded by the final metadata commit)

## Files Created/Modified
- `echo/llm_client.py` - Single network point `post_chat` plus `json_schema_format`, `json_instruction`, `build_messages`, `parse_json_content`, `render_sections`, `try_render`, `is_layer_failure`; imports only `json`, `urllib.*`, `echo.errors`
- `echo/transcription_engine.py` - `TranscriptionEngine` with lazy base-model load and `status`/`complete`/`error` queue contract
- `echo/summarization_engine.py` - `SummarizationEngine` (`__init__`, `is_configured`, `set_preset`, `update_config`, `_request_content`, `summarize`, `start_summary`, `_run_summary`) delegating to `echo.llm_client`

## Decisions Made
- **`llm_client` is fully stateless:** `self.config` access became an explicit `config` parameter on `post_chat`, and `self._json_instruction` became the module-level `json_instruction`; this is what lets the transport be tested without constructing an engine.
- **`parse_json_content` stayed linear-only:** no `import re` (asserted absent by both the task verify and the harness path), preserving T-260921-04's guarantee that no catastrophic backtracking is possible.
- **`is_layer_failure` kept exact:** `None`/`400`/`422` → `True`; `401`/`403`/`429`/`5xx`/`0` → `False`. Simplifying this would silently retry terminal errors 3× (T-260921-05).
- **Deleted, not re-implemented:** the eight helpers are gone from `SummarizationEngine`; `hasattr` assertions confirm the class exposes only `_request_content` and `summarize` as ladder members.
- **Preset validation preserved:** `__init__` reads `summary_preset` from the user-editable config as a registry key only, falling back to `DEFAULT_PRESET` (`free`) when unknown (T-260921-01 / T-06-02).
- **`update_config` keeps `"summary_preset": self.preset`** so a SAVE in API SETTINGS cannot wipe the chosen preset.

## Deviations from Plan

None - plan executed exactly as written.

Two environment accommodations (no deliverable impact):
- The plan's inline `<verify><automated>` one-liners use bash-style `\"` escaping, which PowerShell 5.1 does not honor (it terminates the string at the embedded `"`). The identical assertions were run from a transient script in `%TEMP%\opencode` instead; every check and expected output (`LLM_CLIENT_OK`, `ENGINE_OK`, `ENGINE_DELEGATION_OK`, `SMOKE_SUMMARIZE_ALL_PASS`) was reproduced verbatim.
- `PYTHONPATH=A:\Repos\Echo` was set when invoking the `%TEMP%` harness, because Python puts the *script's* directory on `sys.path` (not the cwd); without it `import echo` / `import main` would not resolve. No test semantics changed.

## Issues Encountered
None. All compile, golden-value, delegation and no-network ladder checks passed on the first run. The transient harness is intentionally not committed (CONTEXT.md defers a permanent `tests/` package).

## User Setup Required
None - no external service configuration required. No real network calls were made; the harness patches `urllib.request.urlopen` and `app_config.json` (the live API key) was neither read nor modified.

## Known Stubs
None. All three modules are fully implemented. `parse_json_content` returning `None` and `is_layer_failure` returning `False` are deliberate, verified outcomes of the layer contract — not placeholders.

## Threat Flags
None. The new files introduce no network endpoint, auth path or trust-boundary surface beyond the plan's `<threat_model>`. Mitigations in place and verified: T-06-01 (api_key only in `Authorization`; harness asserts it is absent from the serialized body), T-06-02 (registry-validated preset fallback), T-06-03 (linear-only parse, no regex), T-06-04 (only registry section keys rendered), T-06-05 (`timeout=60` + terminal-error short-circuit).

## Next Phase Readiness
- The non-GUI `echo/` layer is complete and importable with stable contracts: `echo.llm_client`, `echo.transcription_engine`, `echo.summarization_engine`.
- Plans 03-04 (GUI) can now import these exact names; the import direction `ui → engines → (presets/errors/llm_client/config)` is enforced and acyclic.
- `main.py` and `app_config.py` are untouched, so the delete of `app_config.py` remains atomic with the Plan 05 launcher rewrite (no broken intermediate state).
- No blockers.

---
*Phase: 06-refactor-main-into-echo-package*
*Completed: 2026-09-21*

## Self-Check: PASSED

- FOUND: echo/llm_client.py
- FOUND: echo/transcription_engine.py
- FOUND: echo/summarization_engine.py
- FOUND: .planning/phases/06-refactor-main-into-echo-package/06-02-SUMMARY.md
- FOUND: ff536fe (Task 1 commit)
- FOUND: 80b5507 (Task 2 commit)
- FOUND: b3e6271 (Task 3 commit)
