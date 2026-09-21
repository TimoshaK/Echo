---
phase: 06-refactor-main-into-echo-package
plan: 05
subsystem: refactor
tags: [python, launcher, entry-points, pyinstaller, app-config, smoke-harness]

# Dependency graph
requires:
  - phase: 06-refactor-main-into-echo-package (Plan 01)
    provides: "echo.config (repo-root CONFIG_PATH), echo.presets, echo.errors, echo.srt"
  - phase: 06-refactor-main-into-echo-package (Plan 02)
    provides: "echo.llm_client, echo.transcription_engine, echo.summarization_engine"
  - phase: 06-refactor-main-into-echo-package (Plan 03)
    provides: "echo.ui.theme, echo.ui.build, echo.ui.settings_dialog"
  - phase: 06-refactor-main-into-echo-package (Plan 04)
    provides: "echo.ui.app.TranscriberApp (the only symbol the launcher needs)"
provides:
  - "main.py — a 9-line thin launcher (import TranscriberApp + Tk main loop), no re-exports"
  - "echo/__main__.py — alternative entry point enabling py -3 -m echo"
  - "Root app_config.py removed; echo/config.py is the single config module (no split-brain)"
  - "main.spec hiddenimports=['echo'] so PyInstaller analyses the package explicitly"
  - "Full D-05 smoke set green on the refactored tree (compile, import, headless GUI, no-network ladder, root config read)"
affects: [06-06]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Entry point is a 4-line main(): Tk root -> TranscriberApp(root) -> mainloop()"
    - "Dual entry points share the identical launcher body (main.py and echo/__main__.py)"
    - "Duplicate config module deleted atomically with the rewrite of its only importer"

key-files:
  created:
    - echo/__main__.py
  modified:
    - main.py
    - main.spec
  deleted:
    - app_config.py

key-decisions:
  - "main.py carries no re-exports — only the TranscriberApp import and the four-line main() (CONTEXT.md 'чистая структура')"
  - "app_config.py deleted in the same task as the launcher rewrite, keeping the removal atomic with its last importer (RESEARCH §6)"
  - "app_config.json left untouched at the repository root; CONFIG_PATH still resolves via echo/config.py parent.parent (D-02/REFR-03)"
  - "echo/__main__.py duplicates the launcher body verbatim rather than importing main, keeping both entry points independent"
  - "Task 2 is verification-only and changed no files, so it has no commit (same convention as Plans 01 and 04)"

patterns-established:
  - "Thin launcher: entry-point files own no business logic, only the Tk bootstrap"
  - "Post-refactor verification is a full-tree D-05 smoke set, not per-module spot checks"

requirements-completed: [REFR-01, REFR-02, REFR-03]

# Metrics
duration: 3min
completed: 2026-09-21
---

# Phase 6 Plan 05: Thin Launcher + app_config.py Removal Summary

**Reduced `main.py` from a 1467-line monolith to a 9-line thin launcher, added `echo/__main__.py` for `py -3 -m echo`, deleted the duplicate root `app_config.py`, and passed the complete D-05 smoke set on the refactored tree — confirming unchanged behavior and that the root `app_config.json` API key is still read.**

## Performance

- **Duration:** ~3 min
- **Started:** 2026-09-21T17:34:14Z
- **Completed:** 2026-09-21T17:36:54Z
- **Tasks:** 2 (1 implementation + 1 verification-only)
- **Files modified:** 1 created, 2 modified (1 gitignored), 1 deleted

## Accomplishments
- `main.py` is now the locked thin launcher: `import tkinter as tk`, `from echo.ui.app import TranscriberApp`, and a four-line `main()` (`tk.Tk()` → `TranscriberApp(root)` → `root.mainloop()`). Exactly one function, no `app_config` reference, no re-exports.
- `echo/__main__.py` was added so `py -3 -m echo` works as an alternative entry point; both entry points resolve to a callable `main` (`ENTRYPOINTS_OK`).
- The duplicate root `app_config.py` was removed via `git rm` in the same task as the launcher rewrite — atomic with its last importer, so no broken intermediate state and no split-brain config (T-06-08).
- `app_config.json` was left untouched at the repository root (D-02); `echo.config.CONFIG_PATH` still resolves to `A:\Repos\Echo\app_config.json` and the live API key is readable (`CONFIG_OK … PRESET daily`, REFR-03).
- `main.spec` now sets `hiddenimports=['echo']` (the spec is gitignored via `*.spec`, so the change is local-only, as CONTEXT.md anticipated: "не блокер").
- The complete D-05 smoke set is green on the refactored tree: 14 modules compile; the 13-file target structure exists; the headless GUI builds with 5 presets and the config-derived `daily` selection (`HEADLESS_OK daily`); the no-network summarize ladder passes (`SMOKE_SUMMARIZE_ALL_PASS`); entry points resolve (`ENTRYPOINTS_OK`); no stale references remain (`NO_STALE_REFS_OK`).
- Diff scope of the refactor: `main.py` dropped from 1467 lines to 9; the Task 1 commit shows `3 files changed, 17 insertions(+), 1494 deletions(-)` with `app_config.py` deleted.

## Task Commits

Each implementation task was committed atomically:

1. **Task 1: Thin launcher, echo/__main__.py, delete app_config.py, update main.spec** - `5331b2a` (feat)
2. **Task 2: Full end-to-end D-05 smoke on the refactored tree** - verification-only, no file changes (no commit)

**Plan metadata:** (docs: complete plan) - recorded by the final metadata commit

## Files Created/Modified
- `main.py` - Thin launcher: `TranscriberApp` import + 4-line `main()` + `__main__` guard; no re-exports, no business logic
- `echo/__main__.py` - Alternative entry point with the identical launcher body, enabling `py -3 -m echo`
- `main.spec` - `hiddenimports=['echo']` (gitignored, not part of the commit)
- `app_config.py` - **Deleted** (tracked file removed via `git rm`); `echo/config.py` is now the only config module

## Decisions Made
- **No re-exports in `main.py`.** Per CONTEXT.md `<specifics>` ("main.py не должен содержать реэкспортов — чистая структура"), the old monolith's symbols are not re-exported for back-compat; the launcher imports only `TranscriberApp`.
- **Deletion atomic with the launcher rewrite.** `main.py` was the only importer of `app_config`, so removing the module in the same task (RESEARCH §6) guarantees every intermediate state stays green.
- **`echo/__main__.py` duplicates rather than imports `main`.** Keeps the two entry points independent and avoids an entry-point → launcher import edge; the body is the exact four-line bootstrap.
- **`app_config.json` not moved** (D-02); the live API key stays at the repo root and remains gitignored.
- **Task 2 has no commit.** It is a verification-only task that changed no files; all eight D-05 checks passed against the Task 1 tree (same convention as Plan 01 Task 3 and Plan 04 Task 2).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Plan's Task 2 Check 2 substring assertion could not pass as written**
- **Found during:** Task 2 (full D-05 smoke)
- **Issue:** Check 2 asserted `'app_config' not in <source>` for every `.py` file except `main.py`. But `echo/config.py` legitimately contains the token `app_config` because its `CONFIG_PATH` names the file `app_config.json` (and its comments explain the anchor). The plan's own key_link and D-02/REFR-03 *require* that filename, so "fixing the offending module" would have broken REFR-03 — the assertion itself was defective, not the module.
- **Fix:** Ran the check with its clearly stated intent (the plan's must_have: "No remaining source file **imports** app_config"): assert no `.py` file outside `main.py` contains `import app_config` or `from app_config`. Confirmed via Grep that the only `app_config` mentions in the tree are the three filename references in `echo/config.py`.
- **Files modified:** none (verification-only adjustment)
- **Verification:** `IMPORT_GRAPH_OK`; `Grep "(import|from)\s+app_config"` → no files found; all other seven checks unchanged and green.
- **Committed in:** n/a (Task 2 is verification-only; no file changed)

### Environment accommodations (no deliverable impact)

- The plan's inline `<verify><automated>` one-liners use bash-style `\"` escaping, which PowerShell 5.1 terminates early (a known constraint from Plans 02-04). The identical Task 1 assertions were run from a transient script at `%TEMP%\opencode\verify_06_05_task1.py`; `LAUNCHER_OK` was reproduced verbatim.
- `PYTHONPATH=A:\Repos\Echo` was set when invoking the `%TEMP%` summarize harness, because Python puts the *script's* directory (not the cwd) on `sys.path`; without it `import echo` would not resolve. No test semantics changed.

---

**Total deviations:** 1 auto-fixed (Rule 3 blocking — plan verify bug) + 2 environment accommodations
**Impact on plan:** None on behavior, scope or deliverables. The auto-fix corrected an over-broad assertion to match the plan's own stated intent; the required `app_config.json` filename in `echo/config.py` is preserved exactly.

## Issues Encountered
None. All eight D-05 checks passed (Check 2 under the corrected import-intent semantics). The transient Task 1 verify script lives in `%TEMP%\opencode` and is intentionally not committed (CONTEXT.md defers a permanent `tests/` package).

## User Setup Required
None - no external service configuration required. No network calls were made; `app_config.json` was read only to confirm the key is present (asserted via truthiness, never printed).

## Known Stubs
None. `main.py` and `echo/__main__.py` are complete launchers — no placeholders, no hardcoded empty values, no unwired data. `echo/config.py`'s reference to `app_config.json` is a real resource path (verified resolvable), not a stub.

## Threat Flags
None. No new network endpoint, auth path or trust-boundary surface beyond the plan's `<threat_model>`. Mitigations in place and verified: **T-06-08** — `app_config.py` deletion is atomic with the launcher rewrite, and `CONFIG_PATH.parent` is asserted to be the repository root, so no split-brain config is possible; **T-06-23** — `main.spec` sets only `hiddenimports=['echo']` and deliberately does not add `app_config.json` to `datas`, so the API key is not bundled into a distributable artifact; **T-06-01** — the config check prints only the path and preset name, never the key value (assertions use truthiness); **T-06-24** — entry points are imported, not executed, so no Tk main loop can block verification. `app_config.json` was neither modified nor committed.

## Next Phase Readiness
- The locked target structure is complete: `main.py` (thin launcher) + `echo/` package (13 modules) + root `app_config.json`. REFR-01, REFR-02 and REFR-03 are all satisfied on the refactored tree.
- Plan 06 (final parity/visual verification) can now run the manual-only visual comparison from `06-VALIDATION.md`: `py -3 main.py` must render a window identical to baseline `6887892` (title `Echo // Audio Processing Unit`, `900x650`, all panels/preset combobox/save row).
- Both entry points (`py -3 main.py`, `py -3 -m echo`) are available for the visual check.
- No blockers. `main.py` and `app_config.py` cleanup is fully committed; the working tree holds no refactor changes.

---
*Phase: 06-refactor-main-into-echo-package*
*Completed: 2026-09-21*

## Self-Check: PASSED

- FOUND: main.py (9 lines, thin launcher)
- FOUND: echo/__main__.py
- FOUND: main.spec (hiddenimports=['echo'])
- CONFIRMED: app_config.py deleted (git rm)
- CONFIRMED: app_config.json present at repo root (untouched)
- FOUND: 5331b2a (Task 1 commit)
- CONFIRMED: Task 2 verification-only — no commit (no file changes)
