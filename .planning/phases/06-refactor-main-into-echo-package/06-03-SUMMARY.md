---
phase: 06-refactor-main-into-echo-package
plan: 03
subsystem: ui
tags: [python, tkinter, refactor, theme, widget-builders, settings-dialog]

# Dependency graph
requires:
  - phase: 06-refactor-main-into-echo-package (Plan 01)
    provides: "echo.presets (SUMMARY_PRESETS/DEFAULT_PRESET) used by the preset selector"
  - phase: 06-refactor-main-into-echo-package (Plan 02)
    provides: "summarizer contract (config/update_config/preset) read by build and the settings dialog"
provides:
  - "echo.ui.theme: COLORS — the single source of truth for the nine UI colour literals"
  - "echo.ui.build: build_ui + build_header/build_input_panel/build_processing_panel/build_output_panel/build_save_buttons/build_footer/configure_combobox_style (all take app)"
  - "echo.ui.settings_dialog: open_settings(app) — standalone LLM API modal"
  - "echo.ui subpackage marker with no eager submodule imports"
affects: [06-04, 06-05, 06-06]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Builder functions receive the app instance as a parameter (never imported) — breaks the app↔build cycle"
    - "Palette centralised in theme.COLORS; app maps it to legacy <name>_color attributes"
    - "Mechanical self. → app. relocation preserves widget order, options, fonts, colours and grid rows"
    - "Subpackage marker imports no submodules, so import echo.ui stays cheap and acyclic"

key-files:
  created:
    - echo/ui/__init__.py
    - echo/ui/theme.py
    - echo/ui/build.py
    - echo/ui/settings_dialog.py
  modified: []

key-decisions:
  - "build.py header docstring avoids the literal token echoed by the cycle guard (plan's own verify asserts 'echo.ui.app' absent from source)"
  - "Baseline literals #111111 and #666666 are kept as-is in build.py: they are not part of the nine-key COLORS palette, and the action mandates no restyling"
  - "configure_combobox_style(app) is invoked before app.preset_var is created, preserving the load-bearing baseline order"
  - "build_ui calls build_save_buttons before build_footer, matching baseline line order (938 then 944); grid rows 5 and 4 are unchanged"

patterns-established:
  - "App-instance-parameter builder functions: ui → build, never build → ui"
  - "Theme palette as the only source of named colour literals"

requirements-completed: [REFR-01, REFR-02]

# Metrics
duration: 4min
completed: 2026-09-21
---

# Phase 6 Plan 03: echo/ui Foundation (theme, build, settings dialog) Summary

**Relocated `main.py`'s palette, 471-line `_build_ui` and `open_settings` into `echo/ui/` as `theme.COLORS`, eight app-parameter builder functions and a standalone `open_settings(app)` modal — mechanically order-preserving and proven to construct headlessly.**

## Performance

- **Duration:** ~4 min
- **Started:** 2026-09-21T15:50:49Z
- **Completed:** 2026-09-21T15:54:55Z
- **Tasks:** 3
- **Files modified:** 4 created, 0 modified

## Accomplishments
- `echo/ui/` exists with `theme.py`, `build.py` and `settings_dialog.py`; the marker `__init__.py` imports no submodule, so `import echo.ui` pulls neither `whisper` nor `torch` (asserted).
- `echo/ui/theme.py` carries `COLORS` with the nine baseline literals exactly (`bg #252525`, `accent #F2A900`, …, `error #D9534F`).
- `echo/ui/build.py` (535 lines) decomposes the 471-line `_build_ui` into `build_header`, `build_input_panel`, `build_processing_panel`, `build_output_panel`, `build_save_buttons`, `build_footer`, with `configure_combobox_style` and the `build_ui` orchestrator — all taking `app` as their only coupling.
- The load-bearing order is preserved: `app.preset_labels` → SUMMARY PRESET label → `configure_combobox_style(app)` → `app.preset_var` → `app.preset_combo` (style `Echo.TCombobox`) → `app.preset_combo.bind(..., app.on_preset_change)` → `app.summary_btn`.
- `echo/ui/settings_dialog.py` exposes `open_settings(app)` preserving the title, `480x360` geometry, `resizable(False, False)`, `transient`/`grab_set`, the `pad` dict, `show="*"` masking, the Enable-LLM checkbutton (`selectcolor=app.panel_dark`) and the SAVE button styling.
- The import cycle guard holds: `echo/ui/build.py` neither imports the app module nor contains its dotted name (asserted); the app instance is the only channel from `echo.ui.app` (Plan 04) into the builders.
- Baseline untouched and still green: `main.py`/`app_config.py` unchanged, `main.TranscriberApp` constructs headlessly (`BASELINE_APP_OK daily 5`).

## Task Commits

Each task was committed atomically:

1. **Task 1: Create echo/ui/__init__.py and echo/ui/theme.py** - `1fcc81c` (feat)
2. **Task 2: Create echo/ui/build.py with decomposed widget builders** - `43bbd77` (feat)
3. **Task 3: Create echo/ui/settings_dialog.py** - `dc44e84` (feat)

**Plan metadata:** (docs: complete plan) - recorded by the final metadata commit

## Files Created/Modified
- `echo/ui/__init__.py` - Subpackage marker docstring only; no `from . import ...`
- `echo/ui/theme.py` - `COLORS` dict (9 keys) — the UI palette source of truth
- `echo/ui/build.py` - `build_ui`, `build_header`, `build_input_panel`, `build_processing_panel`, `build_output_panel`, `build_save_buttons`, `build_footer`, `configure_combobox_style`
- `echo/ui/settings_dialog.py` - `open_settings(app)` LLM API modal

## Decisions Made
- **Docstring wording (cycle guard).** The plan's suggested header for `build.py` contained the literal `echo.ui.app`, but the plan's own automated verify asserts `'echo.ui.app' not in src`. The verify is the enforced contract, so the docstring says "the app module" instead. Behaviour and the import graph are unaffected.
- **`#111111` / `#666666` kept.** The nine-key `COLORS` palette has no slot for the near-black on-accent foreground or the disabled foreground, and the action forbids restyling. These two baseline literals therefore stay in `build.py`; the verify only forbids the accent literal `#F2A900`, which is correctly routed through `app.accent_color`.
- **Order preserved literally.** `build_save_buttons` runs before `build_footer` because that is the baseline call order (938 before 944); grid rows are unchanged (save_frame row 5, footer row 4), so layout is identical.
- **`settings_dialog` is stateless.** The key is read from `app.summarizer.config["llm"]` for display and only written back through `app.summarizer.update_config(...)`; the module has no `print`/`logging`.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Plan docstring contradicted its own automated verify**
- **Found during:** Task 2 (`echo/ui/build.py`)
- **Issue:** The plan's suggested module header embedded the literal string `echo.ui.app`, while the same task's `<verify><automated>` asserts `'echo.ui.app' not in src`. Executing the plan verbatim could not pass its own gate.
- **Fix:** Phrased the header as "must NOT import the app module", omitting the forbidden dotted token. No code, imports or behaviour changed.
- **Files modified:** `echo/ui/build.py`
- **Verification:** `PLAN_06_03_VERIFY_OK` (asserts the token is absent and all eight builders are callable).
- **Committed in:** `43bbd77` (Task 2 commit)

### Plan-clarification (not a code deviation)

- The `<done>` bullet "no hard-coded colour literals remain in `build.py`" cannot hold under the locked nine-key `COLORS` palette plus the "do not restyle" action: `#111111` and `#666666` are baseline literals with no palette key. Resolved in favour of behaviour preservation; the automated verify (which only forbids `#F2A900`) passes.

### Environment accommodations (no deliverable impact)

- The inline `<verify><automated>` one-liners use bash `\"` escaping, which PowerShell 5.1 terminates early. The identical assertions were run from transient scripts in `%TEMP%\opencode` with `PYTHONPATH=A:\Repos\Echo`; every expected marker (`THEME_OK`, `BUILD_OK`, `DIALOG_OK`) was reproduced verbatim.
- Two extra transient smoke checks were added (no production code): a stub-app `build_ui` headless construction asserting the 16-widget manifest, 5 preset labels, `Дейли` preset value and `Echo.TCombobox` style (`BUILD_SMOKE_OK`), and a stub-app `open_settings` open asserting a single `API Settings` Toplevel (`DIALOG_SMOKE_OK`).

---

**Total deviations:** 1 auto-fixed (Rule 3 blocking) + 1 plan-clarification + 2 environment accommodations
**Impact on plan:** None on behaviour or scope. The auto-fix was required to satisfy the plan's own verification; the extra smokes only strengthen the behaviour-preservation evidence.

## Issues Encountered
None. One transient-script assertion (reading a `ttk` widget's `state` via `cget`) needed a `str()` coercion because tkinter returns a `Tcl_Obj`; corrected in the throwaway script only. The dialog's `geometry()` readback is `1x1+0+0` under a withdrawn root, so the extra smoke asserts construction + title instead — the plan's verify already asserts the `480x360` literal in source.

## User Setup Required
None - no external service configuration required.

## Known Stubs
None. All four modules are fully implemented. The two baseline literals `#111111`/`#666666` are deliberate preserved styling, not stubs, and `preset_labels` is populated from the live `SUMMARY_PRESETS` registry.

## Threat Flags
None. No new network endpoint, auth path or trust-boundary surface beyond the plan's `<threat_model>`. Mitigations verified: T-06-01 — `show="*"` retained and the module has no `print`/`logging`, so the key can only reach the gitignored config via `update_config`; T-06-14 — `configure_combobox_style` keeps the `try/except tk.TclError: pass` guard verbatim. `app_config.json` was neither read nor modified; no secret is embedded anywhere.

## Next Phase Readiness
- Plan 04 (`echo/ui/app.py`) can now import `echo.ui.build` and `echo.ui.settings_dialog` and construct `TranscriberApp`; `build_ui(self)` requires the colour attributes (`bg_color` … `error_color`) and `self.summarizer` to exist **before** the call.
- The widget manifest Plan 04 must expose: `select_btn`, `file_var`, `file_entry`, `transcribe_btn`, `status_indicator`, `status_label`, `settings_btn`, `preset_labels`, `preset_var`, `preset_combo`, `summary_btn`, `result_text`, `result_scrollbar`, `language_label`, `save_txt_btn`, `save_srt_btn`.
- The import graph is acyclic and ready to extend: `build.py` imports only `tkinter`/`ttk` and `echo.presets`; the reverse edge (`app → build`) is the only coupling.
- No blockers. `main.py` stays intact until Plan 05, so no broken intermediate state.

---
*Phase: 06-refactor-main-into-echo-package*
*Completed: 2026-09-21*

## Self-Check: PASSED

- FOUND: echo/ui/__init__.py
- FOUND: echo/ui/theme.py
- FOUND: echo/ui/build.py
- FOUND: echo/ui/settings_dialog.py
- FOUND: .planning/phases/06-refactor-main-into-echo-package/06-03-SUMMARY.md
- FOUND: 1fcc81c (Task 1 commit)
- FOUND: 43bbd77 (Task 2 commit)
- FOUND: dc44e84 (Task 3 commit)
