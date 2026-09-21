# Phase 6: Refactor main.py into echo package — Technical Research

**Researched:** 2026-09-21
**Baseline commit:** `688789297ed3028dcff56cc55d062f75f8edd0ab`
**Working tree at research time:** clean (`git status --short` → empty)

> Scope note: this is a **behavior-preserving internal refactor**. There are no new
> libraries, no new external integrations and no architectural choices left open —
> the target structure is locked in ROADMAP.md §Phase 6 and CONTEXT.md. Discovery
> level is **0 (skip)**: every pattern is already established in this codebase.

---

## 1. Verified baseline (environment + smoke)

The `D-05` smoke harness was executed against the pre-refactor tree. All checks pass,
so these commands are usable as regression gates *after* each migration step.

| Check | Command | Verified result |
|-------|---------|-----------------|
| Toolchain | `py -3 --version` | `Python 3.14.3` |
| Deps present | `py -3 -c "import whisper, torch, tkinter; print(torch.__version__, tkinter.TkVersion)"` | `2.14.0+cu130` / `8.6` |
| Compile | `py -3 -m py_compile main.py app_config.py` | exit 0 |
| Config | `py -3 -c "import app_config; c=app_config.load_config(); print(app_config.CONFIG_PATH, bool(c['llm']['api_key']))"` | `A:\Repos\Echo\app_config.json` / `True` |
| Headless GUI | `py -3 -c "import tkinter as tk, main; r=tk.Tk(); r.withdraw(); a=main.TranscriberApp(r); print('HEADLESS_OK')"` | `HEADLESS_OK` |
| No-network ladder | `py -3 %TEMP%\opencode\echo_smoke_summarize.py main` | `SMOKE_SUMMARIZE_ALL_PASS` |

`whisper` and `torch` are **installed and importable**, so the headless GUI check is
genuinely runnable in this environment (it is not a placeholder gate).

---

## 2. Extraction map (source → target)

Line numbers refer to `main.py` at the baseline commit.

| Source (`main.py`) | Target module | Symbols |
|---|---|---|
| `app_config.py` (whole file, 40 lines) | `echo/config.py` | `CONFIG_PATH`, `DEFAULT_CONFIG`, `load_config`, `save_config` |
| 17–76 | `echo/presets.py` | `DEFAULT_PRESET`, `SUMMARY_PRESETS` |
| 79–90 | `echo/errors.py` | `SummaryApiError` |
| 1432–1443 (ladder inside `_handle_transcription_error`) | `echo/errors.py` | `map_transcription_error(error) -> str` (new pure function) |
| 1049–1055 (`_time_to_srt`) | `echo/srt.py` | `time_to_srt(seconds, offset=0.0)` |
| 1062–1069 (`_srt_content`) | `echo/srt.py` | `build_srt_content(segments)` |
| 181–222 (`_post_chat`) | `echo/llm_client.py` | `post_chat(config, payload)` |
| 224–255 (`_json_schema_format`) | `echo/llm_client.py` | `json_schema_format(preset)` |
| 257–267 (`_json_instruction`) | `echo/llm_client.py` | `json_instruction(preset)` |
| 269–297 (`_build_messages`) | `echo/llm_client.py` | `build_messages(preset, text, json_mode)` |
| 299–338 (`_parse_json_content`) | `echo/llm_client.py` | `parse_json_content(content)` |
| 340–372 (`_render_sections`) | `echo/llm_client.py` | `render_sections(preset, data)` |
| 391–398 (`_try_render`) | `echo/llm_client.py` | `try_render(preset, content)` |
| 400–411 (`_is_layer_failure`) | `echo/llm_client.py` | `is_layer_failure(exc)` |
| 93–140 | `echo/transcription_engine.py` | `TranscriptionEngine` |
| 143–179, 374–389, 413–474 | `echo/summarization_engine.py` | `SummarizationEngine` (`__init__`, `is_configured`, `set_preset`, `update_config`, `_request_content`, `summarize`, `start_summary`, `_run_summary`) |
| 483–491 (color literals) | `echo/ui/theme.py` | `COLORS` dict |
| 508–979 (`_build_ui`) | `echo/ui/build.py` | `build_ui(app)` + `build_header` / `build_input_panel` / `build_processing_panel` / `build_output_panel` / `build_footer` |
| 981–1001 (`_configure_combobox_style`) | `echo/ui/build.py` | `configure_combobox_style(app)` |
| 1012–1047 (`_build_save_buttons`) | `echo/ui/build.py` | `build_save_buttons(app)` |
| 1305–1421 (`open_settings`) | `echo/ui/settings_dialog.py` | `open_settings(app)` |
| 477–508, 1003–1011, 1071–1124, 1125–1303, 1423–1457, 1460–1463 | `echo/ui/app.py` | `TranscriberApp` (+ `main()` body moves to the launcher) |

**Boundary rule locked by CONTEXT.md:** `echo/srt.py` holds **only pure functions**.
Anything that touches `filedialog` / `messagebox` (`save_transcription_txt`,
`save_transcription_srt`) stays in `echo/ui/app.py`.

**Boundary rule locked by CONTEXT.md:** `echo/errors.py` = `SummaryApiError` +
`map_transcription_error()`. The LLM-specific layer contract `is_layer_failure` lives in
`echo/llm_client.py` (it is tightly coupled to `SummaryApiError.code` semantics of the
request ladder).

---

## 3. The CONFIG_PATH pitfall (highest-risk item, REFR-03)

`app_config.py` currently anchors the config next to itself:

```python
CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "app_config.json")
# → A:\Repos\Echo\app_config.json
```

A naive move of this file to `echo/config.py` makes `__file__` point at `echo/`, so
`CONFIG_PATH` becomes `A:\Repos\Echo\echo\app_config.json` — a file that does not exist.
`load_config()` swallows `FileNotFoundError` and returns `DEFAULT_CONFIG`, so the app
starts happily with `api_key == ""` and `enabled == False`. **The failure is silent.**
That is exactly the REFR-03 regression this phase must not ship.

Required form (D-01):

```python
CONFIG_PATH = Path(__file__).resolve().parent.parent / "app_config.json"
```

Additional trap: `app_config.json` is listed in `.gitignore` and contains the live API
key. A `git clean`/fresh clone will not have it. Therefore the automated check must
assert **the path shape** (parent is the repo root, not `echo/`) as the primary
regression guard, and report key presence as a secondary observation.

---

## 4. Import graph (no cycles allowed)

Locked direction from CONTEXT.md: `ui → engines → (presets / errors / llm_client / config)`.

```
echo/__init__.py            (no imports — keeps `import echo` cheap)
   │
echo/config.py              → json, pathlib
echo/presets.py             → (nothing)
echo/errors.py              → (nothing)
echo/srt.py                 → (nothing)
echo/llm_client.py          → json, urllib.request, urllib.error, echo.errors
echo/transcription_engine.py→ queue, threading, whisper
echo/summarization_engine.py→ queue, threading, echo.config, echo.presets, echo.errors, echo.llm_client
   │
echo/ui/theme.py            → (nothing)
echo/ui/build.py            → tkinter, tkinter.ttk, echo.presets
echo/ui/settings_dialog.py  → tkinter
echo/ui/app.py              → os, queue, tkinter(.filedialog/.messagebox), echo.srt,
                              echo.errors, echo.presets, echo.transcription_engine,
                              echo.summarization_engine, echo.ui.theme,
                              echo.ui.build, echo.ui.settings_dialog
main.py                     → tkinter, echo.ui.app     (thin launcher, NO re-exports)
```

Rules that keep this acyclic and cheap:
- `echo/__init__.py` must **not** import submodules. An eager `from . import ui` would
  pull `whisper` + `torch` on every `import echo`, and would also create an import cycle
  risk with `echo.ui.app`.
- `echo/ui/build.py` must not import `echo.ui.app` (it receives the app instance as a
  parameter, typed loosely). This is what breaks the would-be `app ↔ build` cycle.
- `echo/ui/app.py` imports `build`/`settings_dialog` as modules (`from echo.ui import build`),
  not the reverse.

---

## 5. Verified golden values (regression oracles)

Captured by executing the baseline. These become `<acceptance_criteria>` values.

### SRT

```
time_to_srt(3661.5)                                  == '01:01:01,500'
build_srt_content([{'start':0,'end':1.5,'text':'hello'},
                   {'start':1.5,'end':3.25,'text':' world '}])
  == '1\n00:00:00,000 --> 00:00:01,500\nhello\n\n2\n00:00:01,500 --> 00:00:03,250\nworld\n'
```

Note the second segment proves the `.strip()` on segment text is preserved.

### Presets

```
DEFAULT_PRESET                                        == 'free'
list(SUMMARY_PRESETS)                                 == ['daily','lecture','interview','client','free']
SUMMARY_PRESETS['daily']['sections'][0]['title']       == 'AFD'     # D-04, deliberate — do not "fix"
SUMMARY_PRESETS['free']['schema_name']                 is None
```

### `json_schema_format(SUMMARY_PRESETS['daily'])`

```python
{'type': 'json_schema',
 'json_schema': {'name': 'daily_conspect', 'strict': True,
                 'schema': {'type': 'object',
                            'properties': {'tasks': {'type': 'array', 'items': {'type': 'string'}},
                                           'decisions': {'type': 'array', 'items': {'type': 'string'}},
                                           'blockers': {'type': 'array', 'items': {'type': 'string'}}},
                            'required': ['tasks', 'decisions', 'blockers'],
                            'additionalProperties': False}}}
json_schema_format(SUMMARY_PRESETS['free']) is None
```

### `is_layer_failure` truth table (must be exact)

| `exc.code` | result |
|---|---|
| `None` | `True` |
| `400` | `True` |
| `422` | `True` |
| `401` | `False` |
| `429` | `False` |
| `500` | `False` |
| `0` (network) | `False` |

### `map_transcription_error` (branch assignment verified against baseline)

| probe substring | mapped message |
|---|---|
| `ffmpeg` / `avconv` | `Не установлен ffmpeg. Установите ffmpeg и попробуйте снова.` |
| `format` / `codec` | `Неподдерживаемый формат файла. Используйте MP3, WAV, M4A, FLAC, OGG или WebM.` |
| `model` / `download` | `Не удалось загрузить модель Whisper. Проверьте подключение к интернету.` |
| `memory` / `allocat` | `Недостаточно памяти. Попробуйте файл меньшего размера.` |
| (none of the above) | `Ошибка при обработке аудио. Попробуйте другой файл.` |

**Branch order is significant** and must be preserved exactly: `ffmpeg` is tested before
`format`, and the `model` branch is only reached when `format`/`codec` are absent.

### Summarize ladder (no-network)

Verified against baseline with `urllib.request.urlopen` patched:

| Scenario | Expected |
|---|---|
| Layer 1 (`response_format.type == 'json_schema'`) returns valid JSON | 1 HTTP call, rendered sections returned |
| Layer 1 raises HTTP `400` | 2 HTTP calls; call 2 has `response_format.type == 'json_object'` |
| Layer 1 raises `422`, layer 2 raises `422` | 3 HTTP calls; call 3 has **no** `response_format` key |
| Layer 1 raises HTTP `401` | exactly **1** HTTP call (terminal, no retry), `SummaryApiError.code == 401` |

The harness that produces these results is reproduced verbatim in `06-02-PLAN.md`
Task 3 (transient script, written to `%TEMP%\opencode`, not committed).

---

## 6. Rollout order and the `app_config.py` deletion window

D-03 mandates a staged migration: non-GUI layer first, then GUI, then the launcher.

`main.py` is the **only** importer of `app_config`. During stages 1–4 the new `echo/`
modules are created alongside the untouched `main.py`, so every intermediate state stays
green. Root `app_config.py` is therefore deleted **in the same task that rewrites
`main.py` into the thin launcher** — that keeps the delete atomic with the removal of its
last importer and avoids a broken intermediate state.

```
Plan 01 (wave 1)  echo/__init__, config, presets, errors, srt      main.py untouched, green
Plan 02 (wave 2)  echo/llm_client, transcription_engine, summarization_engine
Plan 03 (wave 3)  echo/ui/__init__, theme, build, settings_dialog
Plan 04 (wave 4)  echo/ui/app
Plan 05 (wave 5)  main.py launcher + echo/__main__.py + DELETE app_config.py + main.spec
```

Consequence to accept explicitly: between Plan 01 and Plan 05 both `app_config.py` and
`echo/config.py` exist. This is temporary duplication, not a second source of truth —
nothing imports `echo.config` until Plan 05. `app_config.json` itself never moves (D-02).

---

## 7. Behavioral risks to watch

| Risk | Why it matters | Guard |
|---|---|---|
| `CONFIG_PATH` drifts into `echo/` | Silent REFR-03 break (see §3) | Path-shape assertion in Plan 01 + Plan 05 |
| `AFD` "corrected" back to `ЗАДАЧИ` | D-04 says `AFD` is deliberate | Literal `'AFD'` assertion in Plan 01 |
| `is_layer_failure` inverted or simplified | Terminal errors (401/429/5xx) would be retried 3× — burns quota/time | Truth-table assertion in Plan 02 |
| `parse_json_content` "improved" with regex | T-260921-04 forbids it; changes parse semantics | Assert only linear ops: no `re.` import in `llm_client.py` |
| API key leaking into error text / request body | T-260921-02 contract | Assert `api_key` appears only in the `Authorization` header; error strings contain no key |
| `summary_preset` from config used unvalidated | T-260921-01 — config file is user-editable | Registry-membership fallback assertion in Plan 02 |
| `_build_ui` decomposition reorders widget creation | `configure_combobox_style` must run before `preset_var`; `preset_labels` before `preset_combo` | Headless GUI smoke asserts `preset_labels` has 5 entries and `preset_var` matches the config preset |
| `main.py` grows re-exports | CONTEXT forbids it ("чистая структура") | `main.py` must not contain the string `app_config`; only `TranscriberApp` import |

---

## Validation Architecture

> Consumed by the plan checker (Dimension 8) and by `06-VALIDATION.md`.

**Framework:** none — this project has no test framework and CONTEXT.md explicitly
defers a permanent `tests/` package to a later phase. Verification is therefore a
**transient smoke harness** (D-05), run inline via `py -3 -c` or via a throwaway script
in `%TEMP%\opencode`. No `tests/` directory, no pytest, no Wave 0 scaffold.

**Because the harness is transient, it is duplicated in the plan that needs it** — the
exact command text lives in each task's `<verify><automated>` block, so verification is
reproducible without any committed test file.

### Verification dimensions

| Dimension | How this phase verifies it | Requirement |
|---|---|---|
| Compilation | `py -3 -m py_compile <files>` exit 0 | REFR-01 |
| Import integrity | `py -3 -c "import <module>"` per module, no side effects | REFR-01 |
| Import graph acyclicity | `py -3 -c "import echo.ui.app"` resolves; no `app_config` in `main.py` | REFR-01 |
| Behavioral equivalence (pure logic) | Golden-value assertions (§5): SRT, presets, schema format, layer-failure table, error mapping | REFR-02 |
| Behavioral equivalence (LLM ladder) | No-network `summarize()` harness with `urllib.request.urlopen` patched (§5) | REFR-02 |
| Behavioral equivalence (GUI) | Headless `tk.Tk(); withdraw(); TranscriberApp(root)` — constructs without exception, preset state matches config | REFR-02 |
| Config contract | `CONFIG_PATH` resolves to repo-root `app_config.json`; `load_config()` returns the live key | REFR-03 |
| Security regressions | API key only in `Authorization` header; preset validated against registry; `parse_json_content` linear-only | T-06-01..T-06-04 |

### Wave 0 assessment

**No Wave 0 required.** The baseline harness was executed and verified green before
planning (see §1), so every `<verify><automated>` in this phase has a runnable command
and a known-good baseline result. There are no `MISSING` automated checks.

### Manual-only verification

One behavior genuinely cannot be automated in this environment: **visual confirmation
that the rendered window is pixel-identical**. The headless check proves construction
succeeds and widget state is correct, but `root.withdraw()` never draws. This is
recorded in `06-VALIDATION.md` as the single manual verification, and it is a
`checkpoint:human-verify` task in Plan 05.

---

## Sources

- `main.py` (baseline `6887892`, 1467 lines) — read in full during research
- `app_config.py` (40 lines), `main.spec`, `app_config.json` (structure only), `.gitignore`
- `.planning/ROADMAP.md` §Phase 6, `.planning/REQUIREMENTS.md` (REFR-01..03), `.planning/STATE.md`
- `.planning/phases/06-refactor-main-into-echo-package/06-CONTEXT.md` (D-01..D-05)
- `.planning/phases/05-packaging-distribution/05-RESEARCH.md` (deferred `CONFIG_PATH`/`%APPDATA%` notes)
