---
phase: 06-refactor-main-into-echo-package
plan: 06
subsystem: refactor
tags: [python, tkinter, widget-parity, visual-verification, human-signoff, app-config]

# Dependency graph
requires:
  - phase: 06-refactor-main-into-echo-package (Plan 01)
    provides: "echo.config (repo-root CONFIG_PATH), echo.presets, echo.errors, echo.srt"
  - phase: 06-refactor-main-into-echo-package (Plan 02)
    provides: "echo.llm_client, echo.transcription_engine, echo.summarization_engine"
  - phase: 06-refactor-main-into-echo-package (Plan 03)
    provides: "echo.ui.theme, echo.ui.build, echo.ui.settings_dialog"
  - phase: 06-refactor-main-into-echo-package (Plan 04)
    provides: "echo.ui.app.TranscriberApp"
  - phase: 06-refactor-main-into-echo-package (Plan 05)
    provides: "Thin main.py launcher, echo/__main__.py, root app_config.json preserved"
provides:
  - "REFR-02 mechanical proof: 50/50 tkinter constructors textually identical to baseline 6887892 (WIDGET_PARITY_EXACT)"
  - "Named human attestation that the rendered window and the select → transcribe → summarize → save workflow are unchanged"
  - "Confirmed root app_config.json remains the config written by API SETTINGS (no echo/app_config.json)"
affects: []

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Transient widget-parity comparator in %TEMP%\\opencode (deliberately not committed), consistent with the D-05 transient-harness approach"
    - "Normalized constructor-multiset comparison against immutable git history as a text-level UI-equivalence proof"

key-files:
  created: []
  modified: []

key-decisions:
  - "Task 1's comparator lives in %TEMP%\\opencode and is intentionally NOT committed (CONTEXT.md defers a permanent tests/ package; D-05 transient harness convention)"
  - "Task 2 (checkpoint:human-verify, gate=blocking) was resolved by the human typing 'approved'; the approval is recorded here as the REFR-02 human attestation rather than inferred (T-06-26)"
  - "No per-task commits for this plan: Task 1 wrote only to %TEMP%, Task 2 changed no files, so the plan produces a single metadata commit"

patterns-established:
  - "Interactive-only behavior (drawn window, workflow) is attested by an explicit human signal recorded in the SUMMARY; mechanical text-level parity covers what the headless smoke cannot"

requirements-completed: [REFR-01, REFR-02]

# Metrics
duration: 1min
completed: 2026-09-22
---

# Phase 6 Plan 06: Widget-Construction Parity + Human Visual Verification Summary

**Proved the refactored UI is textually identical to baseline `6887892` (50/50 tkinter constructors, `WIDGET_PARITY_EXACT`) and recorded the human `approved` sign-off that the drawn window and the select → transcribe → summarize → save workflow are visually and functionally unchanged, with API SETTINGS still writing the root `app_config.json`.**

## Performance

- **Duration:** ~1 min (continuation agent: Task 1 completed previously; Task 2 approval recorded)
- **Started:** 2026-09-22T04:47:19Z
- **Completed:** 2026-09-22T04:48:00Z
- **Tasks:** 2 (1 mechanical parity proof + 1 human-verify checkpoint)
- **Files modified:** 0 (plan `files_modified: []`)

## Accomplishments

- **REFR-02 mechanical proof.** The transient comparator (`%TEMP%\opencode\echo_widget_parity.py`) extracted every `tk.*`/`ttk.*` widget and variable constructor from baseline `main.py` (`git show 6887892:main.py`) and from `echo/ui/build.py` + `echo/ui/settings_dialog.py` + `echo/ui/app.py`, normalized them (whitespace collapse, `self.` → `app.`, drop whitespace before closing paren) and confirmed the multisets are identical. No option, option order, literal value, font, colour, padding, grid row or pack side drifted.
- **Human visual + functional sign-off recorded.** The `checkpoint:human-verify` gate (Task 2, `gate=blocking`) was resolved by the human typing `approved`. The operator confirmed (1) the visual parity checklist, (2) the functional smoke select → transcribe → summarize → save .txt/.srt → API SETTINGS, and (3) that the repository-root `app_config.json` is the file written (no `echo/app_config.json` exists).
- **REFR-03 config regression confirmed.** `PRE_CHECKPOINT_OK` printed: root `app_config.json` exists, `echo/app_config.json` does not, and both entry points (`main.main`, `echo.__main__.main`) resolve to callables.
- Phase 6 is now complete: all three success criteria (unchanged behavior, thin launcher + `echo/` package, root config still loaded) are satisfied.

## Task Commits

This plan produced no per-task commits by design:

1. **Task 1: Mechanical widget-construction parity proof** — transient harness only, written to `%TEMP%\opencode\echo_widget_parity.py` and deliberately not committed (D-05 convention). No repository file changed.
2. **Task 2: Human confirmation that the application is visually and functionally unchanged** — checkpoint task, verification-only, no file changed. Resolved with the human signal `approved`.

**Plan metadata:** recorded by the final metadata commit (docs: complete plan)

_Note: A verification-only plan with `files_modified: []` produces a single metadata commit, matching the Plan 01/04/05 convention for verification-only tasks._

## Files Created/Modified

None. `files_modified` for this plan is `[]`. The factory of evidence was a transient script under `%TEMP%\opencode`, which lives outside the repository.

## Raw Evidence

**Task 1 — mechanical widget parity (reproduced by the continuation agent against the committed tree):**

```
BASELINE_CONSTRUCTORS=50 REFACTORED_CONSTRUCTORS=50
WIDGET_PARITY_EXACT
EXIT=0
```

Comparator: `%TEMP%\opencode\echo_widget_parity.py` (transient, not committed), invoked as
`py -3 "$env:TEMP\opencode\echo_widget_parity.py" 6887892` from the repository root.
Baseline commit: `6887892` (`688789297ed3028dcff56cc55d062f75f8edd0ab`), retrieved via `git show`.

**Task 2 — pre-checkpoint config/entry-point assertion (reproduced):**

```
PRE_CHECKPOINT_OK
EXIT=0
```

Asserts: root `app_config.json` exists; `echo/app_config.json` does **not** exist; `main.main` and
`echo.__main__.main` are callable. The API key value is never read into output (presence only).

## Human Attestation (Task 2)

**Signal:** `approved` (typed by the operator at the blocking `checkpoint:human-verify` gate).

The operator confirmed, against `py -3 main.py`:

- **Visual parity** — window title `Echo // Audio Processing Unit`; `900x650` (min `750x550`); palette `#252525`/`#303030`/`#1D1D1D` with amber `#F2A900`; header `ECHO` / `AUDIO PROCESSING UNIT` / `FICSIT // LOCAL TERMINAL`; `AUDIO INPUT` panel; `TRANSCRIPTION UNIT` / `SYSTEM STATUS` row; `SUMMARY PRESET` clam-styled combobox; `TRANSCRIPTION OUTPUT` + scrollbar; footer `LANGUAGE: --`; `SAVE .TXT` / `SAVE .SRT` row — all present, none missing/duplicated/reordered.
- **Functional smoke on real audio** — select file → `● FILE READY` → transcription with `LANGUAGE: <code>` update → `GENERATE SUMMARY` renders the `====`-ruled summary → `SAVE .TXT` contains transcript + `КОНСПЕКТ` block → `SAVE .SRT` contains `HH:MM:SS,mmm --> HH:MM:SS,mmm` cues → `API SETTINGS` shows the masked key, base URL/model, and `SAVE` preserves the selected preset.
- **Config regression (REFR-03)** — the root `app_config.json` is the file written; `Test-Path echo\app_config.json` is `False`.

## Decisions Made

- **Transient comparator, not a committed test.** Task 1's script stayed in `%TEMP%\opencode`, consistent with CONTEXT.md's deferral of a permanent `tests/` package and the D-05 transient-harness approach. The raw output is the committed evidence instead of the tool.
- **The human approval is recorded, not re-run.** Per the checkpoint resolution, the manual steps were not repeated; the operator's `approved` signal is captured verbatim as the named REFR-02 attestation (T-06-26).
- **No weakened comparator.** The parity check was not relaxed to pass; it reported exact equality using immutable git history and value-preserving normalization only (T-06-27).
- **No per-task commit.** With `files_modified: []`, both tasks altered no repository file; this plan contributes only the final metadata commit.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None. The comparator reported exact parity on the first run and the config/entry-point assertion printed `PRE_CHECKPOINT_OK`; no discrepancy was raised by the operator at the checkpoint.

## User Setup Required

None - no external service configuration required.

## Known Stubs

None. This plan changed no source files. The refactored modules were already complete as of Plans 01–05; no placeholder, hardcoded-empty, or unwired value was introduced or left behind.

## Threat Flags

None. No new network endpoint, auth path, file access pattern or schema change was introduced — this plan modified no files. The plan's `<threat_model>` mitigations hold and were respected during execution:

- **T-06-01 (Information Disclosure):** the live API key was never echoed to the terminal; the config assertion checked presence only, and this SUMMARY contains no key material.
- **T-06-25 (Tampering):** the baseline was read exclusively via `git show` into the transient script; nothing was written into the repository and no stash was applied.
- **T-06-26 (Repudiation):** the `approved` signal is recorded above as an explicit, named human attestation rather than an inferred one.
- **T-06-27 (Tampering):** the comparator normalizes only whitespace and the `self.`→`app.` receiver name; all option names, order and values had to match exactly.

## Next Phase Readiness

- Phase 6 is complete: REFR-01, REFR-02 and REFR-03 are all satisfied on the refactored tree.
- The locked target structure is in place: thin `main.py` launcher + `echo/` package (13 modules) + root `app_config.json`, with `py -3 main.py` and `py -3 -m echo` both working.
- No blockers. The phase's only remaining manual-only verification (rendered-window parity, `06-VALIDATION.md`) is now signed off.

---

*Phase: 06-refactor-main-into-echo-package*
*Completed: 2026-09-22*

## Self-Check: PASSED

- CONFIRMED: `BASELINE_CONSTRUCTORS=50 REFACTORED_CONSTRUCTORS=50` + `WIDGET_PARITY_EXACT` + `EXIT=0` (reproduced)
- CONFIRMED: `PRE_CHECKPOINT_OK` + `EXIT=0` (root `app_config.json` present, `echo/app_config.json` absent, both entry points callable)
- CONFIRMED: human signal `approved` recorded (Task 2, blocking `checkpoint:human-verify`)
- CONFIRMED: no source files modified (`git status --short` shows only `.planning/config.json`, a pre-existing line-ending change, excluded from commits)
- FOUND: 06-06-SUMMARY.md
