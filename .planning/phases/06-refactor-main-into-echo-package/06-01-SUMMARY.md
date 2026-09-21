---
phase: 06-refactor-main-into-echo-package
plan: 01
subsystem: refactor
tags: [python, package-skeleton, config, presets, srt, error-mapping]

# Dependency graph
requires: []
provides:
  - "echo/ package skeleton (importable, no eager submodule imports)"
  - "echo.config: CONFIG_PATH anchored to repo-root app_config.json, load_config/save_config"
  - "echo.presets: DEFAULT_PRESET + SUMMARY_PRESETS registry (single source of truth)"
  - "echo.errors: SummaryApiError + pure map_transcription_error()"
  - "echo.srt: pure time_to_srt() / build_srt_content()"
affects: [06-02, 06-03, 06-04, 06-05, 06-06]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Leaf modules with zero intra-package imports (acyclic base layer)"
    - "Path(__file__).resolve().parent.parent for repo-root-anchored resources"
    - "Pure error-mapping function extracted from a GUI handler"

key-files:
  created:
    - echo/__init__.py
    - echo/config.py
    - echo/presets.py
    - echo/errors.py
    - echo/srt.py
  modified: []

key-decisions:
  - "CONFIG_PATH re-anchored via Path(__file__).resolve().parent.parent (D-01) so it resolves to repo root, not echo/"
  - "echo/__init__.py deliberately imports no submodules (keeps import echo cheap, avoids cycle with echo.ui.app)"
  - "map_transcription_error preserves exact branch order (ffmpeg before format; model only when format/codec absent)"
  - "'AFD' preserved verbatim as the deliberate daily/tasks section title (D-04)"

patterns-established:
  - "Package root is a docstring-only marker; no eager imports"
  - "Repo-root resource resolution via parent.parent, never __file__ parent"

requirements-completed: [REFR-01, REFR-03]

# Metrics
duration: 2min
completed: 2026-09-21
---

# Phase 6 Plan 01: echo Package Skeleton + Leaf Modules Summary

**Created the importable `echo/` package with four dependency-free leaf modules (config, presets, errors, srt) that are behaviorally identical to their `main.py`/`app_config.py` counterparts, with CONFIG_PATH re-anchored to the repository root.**

## Performance

- **Duration:** ~2 min
- **Started:** 2026-09-21T15:38:10Z
- **Completed:** 2026-09-21T15:39:25Z
- **Tasks:** 3 (2 implementation + 1 verification-only)
- **Files modified:** 5 created, 0 modified

## Accomplishments
- `echo/` exists as an importable package whose `__init__.py` pulls in no submodules (importing it does not import `whisper`)
- `echo/config.py` relocates `app_config.py` with `CONFIG_PATH = Path(__file__).resolve().parent.parent / "app_config.json"`, so REFR-03 holds (live API key read from the root config)
- `echo/presets.py` carries the preset registry verbatim, including the deliberate `AFD` title and `free` with `schema_name=None`
- `echo/errors.py` provides `SummaryApiError` plus the pure `map_transcription_error()` extracted from `_handle_transcription_error`, branch order preserved
- `echo/srt.py` provides pure `time_to_srt()` / `build_srt_content()` matching the SRT goldens exactly
- The pre-refactor app remains green: `main.py` and `app_config.py` untouched and `main.TranscriberApp` still constructs headlessly (`BASELINE_APP_OK`, preset `daily`)

## Task Commits

Each implementation task was committed atomically:

1. **Task 1: Create the echo package with config and presets** - `448d041` (feat)
2. **Task 2: Create errors and srt leaf modules** - `7b90baa` (feat)
3. **Task 3: Leaf-layer smoke check and no-regression check on main.py** - verification-only, no file changes (no commit)

**Plan metadata:** (docs: complete plan) - recorded by the final metadata commit

## Files Created/Modified
- `echo/__init__.py` - Package marker docstring only; no eager submodule imports
- `echo/config.py` - `CONFIG_PATH` (repo-root anchored), `DEFAULT_CONFIG`, `load_config`, `save_config`
- `echo/presets.py` - `DEFAULT_PRESET`, `SUMMARY_PRESETS` (daily/lecture/interview/client/free)
- `echo/errors.py` - `SummaryApiError`, pure `map_transcription_error()`
- `echo/srt.py` - pure `time_to_srt()`, `build_srt_content()`

## Decisions Made
- **CONFIG_PATH anchoring (D-01/T-06-08):** used the explicit `Path(__file__).resolve().parent.parent / "app_config.json"` form; verified the resolved parent equals the repo root and is not `echo/`, because `load_config()` swallows `FileNotFoundError` and would otherwise fail silently.
- **`os` dropped for `pathlib`** in `echo/config.py` per D-01; `open()` accepts a `Path`, so `load_config`/`save_config` bodies are otherwise unchanged.
- **`AFD` left untouched** in `SUMMARY_PRESETS["daily"]["sections"][0]["title"]` (D-04) — deliberate, not a typo.
- **`echo/__init__.py` kept import-free** to keep `import echo` cheap and avoid a future cycle with `echo.ui.app`.
- **Task 3 had no commit:** it is a verification-only task that changed no files; all its checks passed against the Task 1-2 tree.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None. One benign environment note: `Get-Date -AsUTC` is unavailable in Windows PowerShell 5.1, so UTC timestamps were produced with `(Get-Date).ToUniversalTime()`; this affected only timing bookkeeping, not any deliverable.

## User Setup Required
None - no external service configuration required.

## Known Stubs
None. All five modules are fully implemented; no placeholder or hardcoded-empty values flow to any consumer. `SUMMARY_PRESETS["free"]["sections"] == []` and `schema_name is None` are intentional registry data (matching baseline), not stubs.

## Threat Flags
None. No new network endpoints, auth paths, or trust-boundary schema changes were introduced. The T-06-08 mitigation (CONFIG_PATH anchor + repo-root assertion) is in place; T-06-01 (no secret in error text) holds — `echo/config.py` adds no logging and no error string containing `api_key`.

## Next Phase Readiness
- Stable contracts are in place for Plan 02: `echo.config`, `echo.presets`, `echo.errors`, `echo.srt` are importable and golden-verified.
- Both `app_config.py` and `echo/config.py` now exist (expected temporary duplication per RESEARCH §6); nothing imports `echo.config` until Plan 05, so there is no split-brain during migration.
- `app_config.json` was not moved or touched (D-02).

---
*Phase: 06-refactor-main-into-echo-package*
*Completed: 2026-09-21*

## Self-Check: PASSED

- FOUND: echo/__init__.py
- FOUND: echo/config.py
- FOUND: echo/presets.py
- FOUND: echo/errors.py
- FOUND: echo/srt.py
- FOUND: .planning/phases/06-refactor-main-into-echo-package/06-01-SUMMARY.md
- FOUND: 448d041 (Task 1 commit)
- FOUND: 7b90baa (Task 2 commit)
