---
phase: 06-refactor-main-into-echo-package
plan: 04
subsystem: ui
tags: [python, tkinter, refactor, transcriber-app, polling-loops, theme-palette, widget-parity]

# Dependency graph
requires:
  - phase: 06-refactor-main-into-echo-package (Plan 01)
    provides: "echo.srt (build_srt_content), echo.errors (map_transcription_error), echo.presets (DEFAULT_PRESET/SUMMARY_PRESETS)"
  - phase: 06-refactor-main-into-echo-package (Plan 02)
    provides: "TranscriptionEngine + SummarizationEngine (queue contracts, preset/config state)"
  - phase: 06-refactor-main-into-echo-package (Plan 03)
    provides: "echo.ui.theme.COLORS, echo.ui.build.build_ui(app), echo.ui.settings_dialog.open_settings(app)"
provides:
  - "echo.ui.app.TranscriberApp — application state, colour attributes, polling loops, event handlers and save actions"
  - "Headless-constructible app: same 16-widget manifest, preset wiring and palette as the main.py baseline"
  - "Delegation seams proven: build_ui(self) / settings_dialog.open_settings(self) / build_srt_content(self.last_segments) / map_transcription_error(error) / theme.COLORS"
affects: [06-05, 06-06]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "App maps theme.COLORS into legacy <name>_color attributes so Plan-03 builders stay unmodified"
    - "Colour attributes and self.summarizer assigned BEFORE build_ui(self) — the builder reads both"
    - "One-line method delegates (open_settings) keep tkinter command= bindings working as bound methods"
    - "GUI module imports no whisper/urllib; all transport stays in the engine layer"

key-files:
  created:
    - echo/ui/app.py
  modified: []

key-decisions:
  - "Colour and preset state are wired before build_ui(self) because build.py reads app.summarizer.preset and every app.<name>_color"
  - "open_settings reduced to a delegate so command=app.open_settings still binds; the 117-line dialog body lives only in echo/ui/settings_dialog.py"
  - "_handle_transcription_error's if/elif ladder replaced by map_transcription_error(error); the widget/messagebox flow is unchanged"
  - "save_transcription_srt writes build_srt_content(self.last_segments) instead of the deleted self._srt_content()"
  - "Task 2 is verification-only and changed no files, so it has no commit (same convention as Plan 01 Task 3)"

patterns-established:
  - "app.py owns state and handlers only; every widget construction, dialog and pure formatter lives in its own module"
  - "Delegation seam is asserted at source level (no colour literals, no whisper/urllib, no relocated method definitions)"

requirements-completed: [REFR-01, REFR-02]

# Metrics
duration: 93min
completed: 2026-09-21
---

# Phase 6 Plan 04: UI Application Window (echo/ui/app.py) Summary

**Relocated `TranscriberApp` out of `main.py` into `echo/ui/app.py` — state, handlers, 100 ms polling loops and save actions — delegating widget construction, the settings dialog, SRT formatting and error mapping to the Plan 01-03 modules, with headless construction proving the same 16-widget manifest, preset wiring and palette as the untouched baseline.**

## Performance

- **Duration:** ~93 min (wall clock; includes environment import cost — `import whisper`/`torch` dominates each smoke run)
- **Started:** 2026-09-21T15:57:39Z
- **Completed:** 2026-09-21T17:31:05Z
- **Tasks:** 2 (1 implementation + 1 verification-only)
- **Files modified:** 1 created, 0 modified

## Accomplishments
- `echo/ui/app.py` (322 lines) now holds `TranscriberApp`: `__init__`, `on_preset_change`, `_base_name`, `save_transcription_txt`, `save_transcription_srt`, `select_file`, `start_transcription`, `poll_progress`, `_handle_transcription_complete`, `_handle_summary_complete`, `_handle_summary_error`, `generate_summary`, `poll_summary`, `open_settings`, `_handle_transcription_error`.
- The five relocated members are gone from the class: `_build_ui` → `build_ui`, `_configure_combobox_style` → `configure_combobox_style`, `_build_save_buttons` → `build_save_buttons`, `_time_to_srt` → `echo.srt.time_to_srt`, `_srt_content` → `echo.srt.build_srt_content`.
- `__init__` maps the nine `theme.COLORS` keys into the legacy `bg_color … error_color` attributes **before** `build_ui(self)` runs, and constructs `self.summarizer` before it too, because the preset selector reads `app.summarizer.preset`.
- `open_settings(self)` is now a one-line delegate to `settings_dialog.open_settings(self)`, keeping the `command=app.open_settings` binding in `build.py` valid.
- `_handle_transcription_error` calls `map_transcription_error(error)` as the single source of error text; the indicator/status/messagebox/button re-enable flow is byte-for-byte the baseline.
- **Widget parity:** all 16 widgets (`select_btn` … `save_srt_btn`) exist on the instance — `WIDGET_PARITY_OK 16`.
- **Preset wiring:** `preset_labels` has 5 entries in registry order, `preset_var` equals `SUMMARY_PRESETS[summarizer.preset]["label"]`, and the combobox uses `Echo.TCombobox` — `PRESET_WIRING_OK daily Дейли`.
- **Colour + title parity:** every `*_color` attribute equals its `COLORS` value and the title is `Echo // Audio Processing Unit` — `COLOR_PARITY_OK`.
- **Helper integration:** `build_srt_content([{'start':0,'end':1.5,'text':'hello'}])` yields the golden SRT and `map_transcription_error('ffmpeg missing')` starts with `Не установлен ffmpeg` — `APP_HELPERS_OK`.
- **Baseline comparison:** the untouched `main.TranscriberApp` passes the identical 16-widget and preset checks — `BASELINE_PARITY_OK`, so the assertions are not weakened.
- No `whisper`/`urllib` import and no colour literal (`#F2A900`) remain in the app module; `main()` is not defined here (it stays with the launcher in Plan 05).

## Task Commits

Each implementation task was committed atomically:

1. **Task 1: Create echo/ui/app.py with TranscriberApp** - `03ddbec` (feat)
2. **Task 2: Headless GUI smoke, widget parity and preset wiring** - verification-only, no file changes (no commit)

**Plan metadata:** (docs: complete plan) - recorded by the final metadata commit

## Files Created/Modified
- `echo/ui/app.py` - `TranscriberApp`: state, palette mapping, polling loops (`root.after(100, ...)`), event handlers and save actions; delegates to `echo.ui.build`, `echo.ui.settings_dialog`, `echo.srt`, `echo.errors`, `echo.ui.theme`

## Decisions Made
- **Order before `build_ui`.** `theme.COLORS` → the nine `*_color` attributes and `self.summarizer` are assigned before `ui_build.build_ui(self)`; `build.py` reads both, so any later assignment would raise. Verified headlessly.
- **`open_settings` as a delegate, not a move.** Keeping a bound-method wrapper preserves `command=app.open_settings` in `build.py` and keeps the dialog body single-sourced in `echo/ui/settings_dialog.py`.
- **Error ladder replaced by `map_transcription_error`.** The branch order (`ffmpeg` before `format`; `model` only when `format`/`codec` absent) now lives once in `echo/errors.py`; the app only formats and shows the message.
- **SRT write delegates to `build_srt_content`.** `self._srt_content()` and `self._time_to_srt()` are deleted from the class; the `.srt` dialog options and the `if not self.last_segments:` guard are unchanged.
- **Task 2 has no commit.** It is a verification-only task that changed no files; all five checks passed against the Task 1 tree.

## Deviations from Plan

None - plan executed exactly as written.

Two environment accommodations (no deliverable impact):
- The plan's inline `<verify><automated>` one-liners use bash-style `\"` escaping, which PowerShell 5.1 terminates early (a known constraint from Plans 02-03). The identical assertions were run from transient scripts in `%TEMP%\opencode`; every expected marker (`APP_SOURCE_OK`, `WIDGET_PARITY_OK 16`, `PRESET_WIRING_OK`, `COLOR_PARITY_OK`, `APP_HELPERS_OK`, `BASELINE_PARITY_OK`, `GUI_SMOKE_OK`) was reproduced verbatim.
- `PYTHONPATH=A:\Repos\Echo` was set when invoking the `%TEMP%` scripts, because Python puts the *script's* directory (not the cwd) on `sys.path`; without it `import echo` / `import main` would not resolve. No test semantics changed.

## Issues Encountered
None. One console-encoding note: the Cyrillic preset label prints as mojibake in the Windows PowerShell code page, but the assertion `a.preset_var.get() == SUMMARY_PRESETS[a.summarizer.preset]["label"]` passed, so the wiring is correct — only the terminal display is affected.

## User Setup Required
None - no external service configuration required.

## Known Stubs
None. The module is fully implemented: every handler, polling loop and action is wired to a real engine/helper. `preset_labels` is populated from the live `SUMMARY_PRESETS` registry and `preset_var` from the live `app_config.json` (`daily`). The empty initial values (`selected_file = None`, `last_transcript = ""`, `last_segments = []`, `last_summary = ""`) are deliberate baseline state, not placeholders.

## Threat Flags
None. No new network endpoint, auth path or trust-boundary surface beyond the plan's `<threat_model>`. Mitigations in place and verified: **T-06-01** — the module imports neither `urllib` nor `json` (asserted), so the API key cannot be read or logged here; no colour literal reaches a widget attribute. **T-06-18** — both loops drain with `get_nowait()` inside `try/except queue.Empty` and reschedule via `root.after(100, ...)`, so an empty queue cannot busy-spin the GUI thread. **T-06-19** — handlers act only on the known `type` values (`status`/`complete`/`error`, `summary_status`/`summary_complete`/`summary_error`); unknown types are ignored. **T-06-07/T-06-20/T-06-21** — accepted, unchanged from the baseline (user-driven `filedialog` paths, self-bound callbacks, `showinfo` confirmation). `app_config.json` was read only through the engines and was neither modified nor committed.

## Next Phase Readiness
- `echo/ui/app.py` exposes `TranscriberApp` with the exact 16-widget manifest, so Plan 05 can reduce `main.py` to `from echo.ui.app import TranscriberApp` + `main()` and delete `app_config.py`.
- Every line of the original `main.py` now has a home in `echo/`; the remaining work is launcher + cleanup + end-to-end smoke, plus Plan 06's parity proof / visual verification.
- The import graph stays acyclic: `app.py` consumes `build`/`settings_dialog`/`theme`/`srt`/`errors`/`presets`/engines and nothing imports `app` except the future launcher.
- No blockers. `main.py` and `app_config.py` remain untouched, so no broken intermediate state.
- Deferred (out of scope, per CONTEXT.md): a permanent `tests/` package; the transient `%TEMP%` smoke scripts are intentionally not committed.

---
*Phase: 06-refactor-main-into-echo-package*
*Completed: 2026-09-21*

## Self-Check: PASSED

- FOUND: echo/ui/app.py
- FOUND: .planning/phases/06-refactor-main-into-echo-package/06-04-SUMMARY.md
- FOUND: 03ddbec (Task 1 commit)
- CONFIRMED: Task 2 verification-only — no commit (no file changes)
