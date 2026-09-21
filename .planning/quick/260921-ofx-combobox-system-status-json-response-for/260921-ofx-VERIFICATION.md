---
phase: quick-260921-ofx
verified: 2026-09-21T00:00:00Z
status: human_needed
score: 7/7 must-haves verified
re_verification: false
human_verification:
  - test: "Launch the app (`py -3 main.py`) at 900x650 and inspect the SYSTEM STATUS panel"
    expected: "A dark-themed readonly Combobox labelled SUMMARY PRESET sits between API SETTINGS and GENERATE SUMMARY, shows 5 options (Дейли / Лекция / Интервью / Клиент / Свободный), starts on the saved preset, and the panel does not jump relative to TRANSCRIPTION UNIT"
    why_human: "Visual appearance / layout stability of a ttk.Combobox cannot be verified headlessly; the code has a safe theme fallback (tk.TclError swallowed) but the rendered look is not programmatically assertable"
  - test: "With a valid API key, run one live summarize using the Дейли preset (or call summarize(text, 'daily'))"
    expected: "Request succeeds via the json_schema layer and the output contains headings ЗАДАЧИ / РЕШЕНИЯ / БЛОКЕРЫ; on a provider that rejects response_format the output still renders via json_object or plain text"
    why_human: "External LLM service integration; depends on live quota/network and provider support for response_format. Plan marks this E2E as optional and explicitly excluded from mandatory verification"
---

# Phase quick-260921-ofx: Summary Presets Verification Report

**Phase Goal:** Пресеты конспектов: Combobox в панели SYSTEM STATUS (дейли/лекция/интервью/клиент/свободный), своя JSON-схема на каждый тип через `response_format`; слоистый fallback `json_schema -> json_object -> plain text`; рендер JSON в разделы; персист пресета в `app_config.json`; free без `response_format`

**Verified:** 2026-09-21
**Status:** human_needed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
| --- | ----- | ------ | -------- |
| 1 | Combobox (readonly) with 5 presets Дейли/Лекция/Интервью/Клиент/Свободный in `status_panel` | ✓ VERIFIED | `main.py:793-821` builds `preset_combo` with `state="readonly"`, values from `preset_labels` (order = `SUMMARY_PRESETS`). Headless test: `cget("state")=="readonly"`, values exactly the 5 labels. |
| 2 | Selection persisted to `llm.summary_preset` and restored next launch | ✓ VERIFIED | `set_preset` (`main.py:162-168`) writes via `app_config.save_config`; `__init__` reads/restores (`main.py:151-154`). Temp-config test: set → file updated; new engine reads `daily`. Real `app_config.json` backfilled to `free`. |
| 3 | daily/lecture/interview/client send `response_format json_schema`; layer failure (400/422, empty/unexpected, unusable JSON) → `json_object`; both fail → plain text | ✓ VERIFIED | `_json_schema_format` (`main.py:224-255`), ladder in `summarize` (`main.py:434-458`). Harness: 1 call on clean JSON; 2 calls on 400/422/non-JSON/unknown-keys/list; 3 calls (no `response_format` on 3rd) when both layers fail. |
| 4 | Terminal errors (401/403/429/5xx/network 0) shown immediately, no retries; layer failure does not break ladder | ✓ VERIFIED | `_is_layer_failure` (`main.py:400-411`) is the sole classifier. Harness: each of 401/403/429/500/0 → exactly 1 call, propagated as `SummaryApiError` with code preserved; `None/400/422` → `True`. |
| 5 | `free` sends no `response_format` | ✓ VERIFIED | `summarize` short-circuits `schema_name is None` → `_request_content(..., None)` (`main.py:430-432`); payload omits the key (`main.py:387-388`). Harness confirmed no `response_format` key. |
| 6 | JSON rendered into readable sections and same text stored in `self.last_summary`, so .txt export works unchanged | ✓ VERIFIED | `_render_sections` (`main.py:340-372`) → `summary_complete` (`main.py:468-474`) → `_handle_summary_complete` sets `self.last_summary` (`main.py:1250`). Harness: rendered output contains headings/bullets/`нет данных`, no `КОНСПЕКТ` double-header; `_handle_summary_complete` sets `last_summary`; `save_transcription_txt` writes transcript + exactly one `КОНСПЕКТ` block + summary. |
| 7 | Config without `summary_preset` loads `free` (backfill); API SETTINGS SAVE does not wipe preset | ✓ VERIFIED | `app_config.DEFAULT_CONFIG["llm"]["summary_preset"]="free"` (`app_config.py:17`), `setdefault` backfill (`app_config.py:29-32`); `update_config` carries `summary_preset` forward (`main.py:170-179`). Harness on legacy config: engine→`free`; `set_preset("daily")` then `update_config(...)` → file still `daily`, api_key intact. |

**Score:** 7/7 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
| -------- | -------- | ------ | ------- |
| `app_config.py` | default `llm.summary_preset = free` + backfill | ✓ VERIFIED | Line 17 default; `load_config`/`save_config` `setdefault`/update loops give backward-compatible backfill. |
| `main.py` | `SUMMARY_PRESETS` registry + layered `summarize` + section render + Combobox | ✓ VERIFIED | Lines 23-76 registry (5 presets, locked sections, order); lines 413-458 ladder; 340-372 render; 793-821 Combobox. |
| `main.py` | `class SummaryApiError` with code | ✓ VERIFIED | Lines 79-90; `code: int | None`, subclasses `RuntimeError`. |
| `main.py` | single classifier `_is_layer_failure` | ✓ VERIFIED | Lines 400-411. |
| `main.py` | `self.preset_combo` selector bound to engine/config | ✓ VERIFIED | Lines 811-821; bound to `on_preset_change` (1003-1010). |

### Key Link Verification

| From | To | Via | Status | Details |
| ---- | -- | --- | ------ | ------- |
| `TranscriberApp.on_preset_change` | `app_config.save_config` | `SummarizationEngine.set_preset` | ✓ WIRED | `on_preset_change` → `set_preset` (main.py:1007) → `save_config` (main.py:168). Verified persisted in temp config. |
| `SummarizationEngine.summarize` | `{base_url}/chat/completions` | `payload['response_format']` | ✓ WIRED | `_request_content` sets it only when non-None (main.py:387-389); `_post_chat` POSTs payload (main.py:190-203). |
| `TranscriberApp._handle_summary_complete` | `self.last_summary` | rendered text from `summary_complete` | ✓ WIRED | main.py:1250; harness confirmed. |
| `TranscriberApp._build_ui` | `SUMMARY_PRESETS` | `ttk.Combobox` values | ✓ WIRED | main.py:793-814; values match registry order. |
| `SummarizationEngine.update_config` | `llm.summary_preset` | preserving preset on llm rewrite | ✓ WIRED | main.py:177; harness confirmed preset survives. |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
| -------- | ------------- | ------ | ------------------ | ------ |
| `SummarizationEngine.summarize` | returned sections | `_post_chat` → `message["content"]` → `_parse_json_content` → `_render_sections` | Yes (real API content, JSON parsed to registry keys) | ✓ FLOWING |
| `TranscriberApp._handle_summary_complete` | `self.last_summary` | `summary_complete` queue message produced by `_run_summary` from `summarize` return | Yes (rendered text, not placeholder) | ✓ FLOWING |
| `save_transcription_txt` | `content` | `self.last_summary` | Yes (verified file content contained transcript + summary) | ✓ FLOWING |

### Behavioral Spot-Checks

Harness: throwaway script outside repo (`Temp\opencode`), `py -3` from `A:\Repos\Echo`, all network/`urlopen` patched. Exit 0, `FAIL_COUNT 0`.

| Behavior | Command | Result | Status |
| -------- | ------- | ------ | ------ |
| Syntax compiles | `py -3 -m py_compile main.py app_config.py` | exit 0 | ✓ PASS |
| Registry order/sections/free schema | in-harness asserts | exact match, free `schema_name is None`, `sections == []` | ✓ PASS |
| Classifier `{None,400,422}` vs terminal | in-harness asserts | 9 codes classified correctly | ✓ PASS |
| Ladder call counts / response_format | patched `_post_chat` route | 1 / 2 / 3 calls as designed; 3rd layer omits `response_format` | ✓ PASS |
| Terminal propagation | patched `_post_chat` raise | 401/403/429/500/0 → 1 call, `SummaryApiError.code` preserved | ✓ PASS |
| `reasoning_content` ignored | real `_post_chat`, patched `urlopen` | returns exactly `content`; no leak into result; `Authorization` header present; api_key absent from messages | ✓ PASS |
| Empty/bad-shape content | real `_post_chat`, patched `urlopen` | `SummaryApiError(code=None)`, `_is_layer_failure` True | ✓ PASS |
| Headless GUI build | `tk.Tk(); withdraw(); TranscriberApp(root)` | built with no exception; readonly combo, 5 values | ✓ PASS |
| Persist/backfill/update_config | temp `CONFIG_PATH` | set/reset persisted; legacy config→`free`; `update_config` preserved preset + api_key | ✓ PASS |
| .txt export | patched dialog/messagebox | transcript + single `КОНСПЕКТ` block + rendered summary | ✓ PASS |
| Real config untouched | read `app_config.json` | `preset=free`, model/base_url/enabled/key_len unchanged | ✓ PASS |

Step 7b: run. No live network used.

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
| ----------- | ----------- | ----------- | ------ | -------- |
| SUMR-01 | quick plan | Generate a short summary of the transcription in one action | ✓ SATISFIED | `generate_summary`/`summarize` intact and extended with presets; rendered sections reach `last_summary`. |
| SUMR-02 | quick plan | Pluggable LLM provider (configurable base URL + API key), independent | ✓ SATISFIED | Provider-independent layers (`json_schema`→`json_object`→plain) with single `_post_chat`; config `base_url`/`api_key` unchanged and preserved. |

No orphaned requirements: REQUIREMENTS.md maps SUMR-01/02 only to Phase 3 (already Complete); this quick task is an enhancement of the same IDs, covered by the plan.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
| ---- | ---- | ------- | -------- | ------ |
| — | — | No TODO/FIXME/placeholder/stub markers in `main.py` / `app_config.py` | ℹ️ Info | Empty list/dict initializations found (`properties`, `required`, `blocks`, `items`, `last_segments`, `lines`) are legitimate accumulators/initial state, not stubs. |

### Human Verification Required

1. **Preset Combobox visual/layout check**
   **Test:** `py -3 main.py`, inspect SYSTEM STATUS at 900x650.
   **Expected:** Dark readonly Combobox "SUMMARY PRESET" between API SETTINGS and GENERATE SUMMARY, 5 options, starts on saved preset, panel alignment stable.
   **Why human:** Visual rendering/theme cannot be asserted headlessly (theme fallback is intentionally silent).

2. **Live LLM E2E (optional per plan)**
   **Test:** one `summarize(text, "daily")` with a real key.
   **Expected:** JSON via `json_schema` renders ЗАДАЧИ / РЕШЕНИЯ / БЛОКЕРЫ; providers rejecting `response_format` still produce output via `json_object`/plain text.
   **Why human:** External service integration depends on live network/quota/provider support; plan explicitly excludes it from mandatory verification.

### Gaps Summary

No gaps found. All 7 must-have truths, 5 artifacts, and 5 key links verified against actual code (commit `7ac7418` HEAD). In-repo config preserved at `summary_preset: free` with credentials intact. The only outstanding items are human/visual and live-service checks listed above, which are outside programmatic reach.

---

_Verified: 2026-09-21_
_Verifier: the agent (gsd-verifier)_
