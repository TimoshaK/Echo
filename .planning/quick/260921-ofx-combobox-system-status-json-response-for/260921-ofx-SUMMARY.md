---
phase: quick-260921-ofx
plan: 01
subsystem: [ui, api]
tags: [tkinter, ttk, combobox, openai-compatible, response_format, json_schema, json_object, whisper-transcriber, presets]

# Dependency graph
requires:
  - phase: 03-01
    provides: SummarizationEngine.summarize + API settings dialog (OpenAI-compatible chat/completions)
  - phase: 04-01
    provides: save_transcription_txt with КОНСПЕКТ block fed from self.last_summary
provides:
  - SUMMARY_PRESETS registry (daily/lecture/interview/client/free) with per-preset sections
  - Layered response_format fallback json_schema -> json_object -> plain text
  - summary_preset persistence in app_config.json (llm.summary_preset)
  - readonly preset Combobox in SYSTEM STATUS panel
affects: [summarization, export-txt, api-settings]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Single network path (_post_chat) + single error classifier (_is_layer_failure)"
    - "ASCII JSON schema keys mapped to Russian section titles at render time"
    - "Preset registry dict order drives Combobox order"
    - "Config value used only as registry key, always validated"

key-files:
  created: []
  modified:
    - main.py
    - app_config.py

key-decisions:
  - "ASCII section keys (tasks/decisions/...) in schema + JSON instruction, mapped to RU headings at render — works in both json_schema and json_object layers"
  - "Layer failure = code in {None, 400, 422}; everything else (401/403/429/5xx/network 0) is terminal and never retried"
  - "max_tokens is never set: reasoning models truncate into reasoning_content and return empty content"
  - "reasoning_content is never read; only message.content is extracted"
  - "Added optional `hint` key to each preset for natural prompt phrasing; registry keys/sections/order unchanged"
  - "update_config rewrites llm dict but carries summary_preset forward so SAVE in API SETTINGS cannot wipe the choice"

# Metrics
duration: ~6min
completed: 2026-09-21
---

# Quick 260921-ofx: Summary Presets (Combobox + JSON response_format) Summary

**Five summary presets with a readonly Combobox in SYSTEM STATUS, per-preset JSON schema and layered `json_schema -> json_object -> plain text` fallback, with the choice persisted to `llm.summary_preset`**

## Performance

- **Duration:** ~6 min
- **Started:** 2026-09-21T17:57Z (approx.)
- **Completed:** 2026-09-21T18:03Z
- **Tasks:** 3
- **Files modified:** 2 (`main.py`, `app_config.py`)

## Accomplishments

- `SUMMARY_PRESETS` registry with 5 presets in locked order (daily / lecture / interview / client / free) and per-preset sections; `free` keeps the previous behaviour and sends no `response_format`.
- `SummarizationEngine` now uses a layered ladder: `json_schema` -> `json_object` (+ JSON instruction) -> plain text. Exactly one request when `json_schema` works, two on 400/422 / empty content / unusable JSON, three as last resort.
- `_post_chat` is the single network path; only `message.content` is read (`reasoning_content` never rendered or stored), and empty/whitespace content is treated as a layer failure (`code=None`) rather than a terminal error.
- `_is_layer_failure` is the single classifier: `{None, 400, 422}` are retryable; `401/403/429/5xx/network(0)` propagate immediately as `SummaryApiError` with no extra calls.
- Rendered sections replace the raw JSON in `self.last_summary`, so `SAVE .TXT` with its `КОНСПЕКТ` block works untouched and there is no duplicate header.
- `llm.summary_preset` is persisted on selection and survives the API SETTINGS SAVE; older configs get `free` via the existing `setdefault` backfill.
- Readonly `ttk.Combobox` (dark `Echo.TCombobox` style, safe theme fallback) sits next to GENERATE SUMMARY and restores the saved preset on startup.

## Task Commits

Each task was committed atomically:

1. **Task 1: Preset registry + llm.summary_preset persistence (contract)** - `06c2553` (feat)
2. **Task 2: Layered response_format fallback + JSON section render** - `13ac954` (feat)
3. **Task 3: Preset Combobox in SYSTEM STATUS** - `7ac7418` (feat)

_No separate `test(...)` commit: the plan mandates verification scripts live outside the repository (`C:\Users\...\Temp\opencode\`, deleted after the run) and that only `main.py`/`app_config.py` be present in the repo. RED was still executed first (see TDD note below). Docs commit for SUMMARY.md/STATE.md left to the orchestrator._

## Files Created/Modified

- `app_config.py` - added `"summary_preset": "free"` to `DEFAULT_CONFIG["llm"]` (one line; existing backfill loops untouched).
- `main.py` - added `DEFAULT_PRESET`, `SUMMARY_PRESETS`, `SummaryApiError`; preset validation in `__init__`; `set_preset()`; `update_config()` preserves preset; rewrote `summarize()` with `_post_chat`, `_json_schema_format`, `_json_instruction`, `_build_messages`, `_parse_json_content`, `_render_sections`, `_request_content`, `_try_render`, `_is_layer_failure`; added `_configure_combobox_style`, `on_preset_change`, and the `preset_combo`/`preset_var`/`preset_labels` UI. `start_summary`, `_run_summary`, queue contract, `generate_summary`, `_handle_summary_complete`, `save_transcription_txt`, `_build_save_buttons` and `open_settings` unchanged.

## Decisions Made

See `key-decisions` frontmatter. Notable ones: ASCII section keys mapped to Russian headings at render time; a single classifier for retry-vs-terminal; never setting `max_tokens`; optionally adding a `hint` per preset for phrasing (registry keys/sections/order untouched).

## Deviations from Plan

### Mandated verification corrections (applied)

The orchestrator flagged two defects in the Task 2 `<verify>` recipe; both were applied in the harness without changing product behaviour:

1. **Case 12 false failure fixed.** The direct `_post_chat(payload)` call now runs in its own `with patch(...)` block (asserting its return, the `Authorization` header and that the api_key is absent from `messages`), and `REQS.clear()` was moved to immediately before `eng.summarize(...)`. The `len(REQS) == 1` assertion now genuinely tests the successful single-request `json_schema` ladder.
2. **Sub-cases 11a/11b scripted.** Added an index-routed `fake_urlopen_seq` over a mutable `SEQ` holder: 11a asserts 2 calls with `response_format` `[json_schema, json_object]` (layer 1 empty -> layer 2 succeeds); 11b asserts 3 calls with `[json_schema, json_object, absent]` (layers 1+2 empty -> plain text). 11c (all three empty -> `SummaryApiError(code=None)` after 3 calls) was kept and upgraded to the same index routing.

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Temp scripts could not import `main`/`app_config`**

- **Found during:** Task 1 verification
- **Issue:** The plan's recipe runs `py -3 <temp script>` from `A:\Repos\Echo`, but Python puts the *script's* directory (not the cwd) on `sys.path`, so `import app_config` raised `ModuleNotFoundError`.
- **Fix:** Ran the harness with `PYTHONPATH=A:\Repos\Echo` (kept scripts outside the repo and ran with repo cwd as the plan requires).
- **Files modified:** none (environment only).
- **Verification:** All three harnesses pass with the corrected invocation.

### Test-harness scope adjustment

**2. Removed one self-authored over-strict assertion**

- **Found during:** Task 2 GREEN run
- **Issue:** An extra scenario (not in the plan) expected a second API call when a valid JSON object contains a known section key but with a non-list value (`{"tasks": "not a list", ...}`). By the plan's own `_render_sections` rules, a present known key is renderable, so the correct behaviour is a single call rendering that section.
- **Fix:** Deleted the extra scenario from the throwaway harness; no product code changed.
- **Files modified:** harness only (deleted).

## Issues Encountered

- No test framework in the project (by plan): verification used throwaway `assert`/`sys.exit(1)` scripts under `C:\Users\...\Temp\opencode\`, all deleted after the run.
- TDD note: RED was confirmed first — the harness failed with `TypeError: summarize() takes 2 positional arguments but 3 were given` against the pre-Task-2 code; GREEN then passed after implementation. No test commit exists because the plan forbids test files in the repo.
- `__pycache__/main.cpython-314.pyc` is tracked in this repo and shows as modified after running Python; it was deliberately **not** staged in any task commit. Pre-existing unrelated working-tree changes (`.planning/REQUIREMENTS.md`, `.planning/ROADMAP.md`, untracked `SETUP_GUIDE.txt`) were left untouched.

## Known Stubs

None. No hardcoded empty values, placeholder text, or unwired components were introduced. `app_config.json` ends at `llm.summary_preset == "free"`, with `api_key`/`base_url`/`model`/`enabled` unchanged (key length 76, `enabled: true`, `https://api.dslab.tech/v1`, `deepseek-v4.1-flash`); the live key was never printed or committed.

## Threat Flags

None. All `<threat_model>` mitigations were implemented:

- T-260921-01 preset validated by registry key in both `__init__`/`set_preset` and `summarize(preset_id)`.
- T-260921-02 error messages carry only `e.code` + `detail[:500]`; api_key only in the `Authorization` header.
- T-260921-03 renderer iterates known registry keys only, `json.loads` only, no `eval`/`exec`.
- T-260921-04 parsing is linear (strip, `find`/`rfind`, `json.loads`), no regex.
- T-260921-05 only `message["content"]` is read; `reasoning_content` never rendered or stored.
- T-260921-06 (accepted) unchanged.

No new network endpoints, auth paths, file access patterns, or schema changes were introduced.

## Verification Evidence

- `py -3 -m py_compile main.py app_config.py` → exit 0
- Task 1 harness → `OK task1`
- Task 2 harness → `PART A OK` / `OK task2` (13 behaviours incl. 8 terminal-code variants, free terminal variants, 11a/11b/11c, 12, unknown-preset fallback; zero real network calls)
- Task 3 harness → `OK task3`
- Headless UI smoke → `UI OK`; regression contract → `True True`; `import main` → `IMPORT OK`
- Final config → `preset: free`, credentials unchanged

## Self-Check

- FOUND: `main.py` contains `SUMMARY_PRESETS`, `class SummaryApiError`, `_is_layer_failure`, `self.preset_combo`
- FOUND: `app_config.py` contains `summary_preset`
- FOUND: `06c2553`, `13ac954`, `7ac7418`
- MISSING: (none)

## Self-Check: PASSED

---

*Quick task: 260921-ofx*
*Completed: 2026-09-21*
