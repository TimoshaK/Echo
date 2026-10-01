---
phase: 09-containerized-gui-delivery
plan: 02
subsystem: infra
tags: [config, env-override, echo-config-path, docker-mount, atomic-write, cntr-03, refr-03, sec-01]

# Dependency graph
requires: []
provides:
  - "echo/config.py resolve_config_path(env) — ECHO_CONFIG_PATH-aware path resolver with an unchanged repository-root default"
  - "CONFIG_PATH = resolve_config_path() module attribute (still patchable by existing tests)"
  - "tests/test_config_env_override.py — 8 unit tests for the override, the preserved default, and a real save/load round-trip"
affects: [plan-09-03, plan-09-04, phase-09-verify-work]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "config location is resolved by a pure helper taking an optional env mapping; the module attribute is computed once at import"
    - "container config is supplied by a DIRECTORY bind mount (/config) + ECHO_CONFIG_PATH, never a single-file bind mount"
    - "behavior-preserving override: no env var => byte-identical default path (REFR-03)"

key-files:
  created:
    - tests/test_config_env_override.py
  modified:
    - echo/config.py

key-decisions:
  - "resolve_config_path(env=None) is pure and injectable (defaults to os.environ); the module keeps CONFIG_PATH a plain attribute so existing tests/test_config_read.py and test_config_write.py monkey-patching still works"
  - "An empty or whitespace-only ECHO_CONFIG_PATH falls back to the repository root, so a blank container env var cannot silently relocate the config"
  - "The override expands ~ but does not resolve/normalize the path, so a relative override is preserved verbatim"
  - "validate_base_url (echo/llm_client.py) is untouched — the mount changes where the config lives, never what a valid base_url is (SEC-02 / T-09-11)"

patterns-established:
  - "Container config is mounted as a directory and addressed via ECHO_CONFIG_PATH; a single-file bind mount would make os.replace fail with EBUSY (research finding, T-09-03)"
  - "Environment-driven behavior is isolated in a pure helper with an explicit env argument, making it testable without mutating the process environment"

requirements-completed: [CNTR-03]

# Metrics
duration: ~2min
completed: 2026-10-01
---

# Phase 9 Plan 02: Config Env Override Summary

**Added an ECHO_CONFIG_PATH override so a container can point the app at a directory-mounted `app_config.json` (`/config/app_config.json`) while the no-env default stays byte-identical to the repository root, leaving the atomic owner-only writer and the https-only endpoint policy untouched**

## Performance

- **Duration:** ~2 min
- **Started:** 2026-10-01T03:44:52Z
- **Completed:** 2026-10-01T03:46:01Z
- **Tasks:** 2
- **Files modified:** 2 (1 modified, 1 created)

## Accomplishments

- **Task 1 — `echo/config.py` gained `resolve_config_path`.** Added `from collections.abc import Mapping` and a pure `resolve_config_path(env=None)` that returns `Path(ECHO_CONFIG_PATH).expanduser()` when the var is set and non-blank, else the unchanged repository-root `app_config.json`. `CONFIG_PATH = resolve_config_path()` remains a plain module attribute, and `load_config` / `save_config` / `_atomic_write_secure` / `_restrict_windows_acl` / `DEFAULT_CONFIG` are unchanged.
- **Task 2 — durable override tests.** `tests/test_config_env_override.py` adds 8 stdlib `unittest` cases (default path, env override, empty/whitespace fallback, `~` expansion, module attribute name, relative-path preservation, and a real `save_config` + `load_config` round-trip through a temp directory). All use temp paths only; the repository `app_config.json` is never read, written, or printed.
- **Verification:** Task 1 static check `OK config override`; Task 2 quick tier 8/8 OK; full suite **129/129 OK** (baseline 121 after 09-01 + 8 new).

## Task Commits

Each task was committed atomically:

1. **Task 1: Add resolve_config_path + ECHO_CONFIG_PATH to echo/config.py** — `6cedcdc` (feat)
2. **Task 2: Add tests/test_config_env_override.py** — `15fd274` (test)

**Plan metadata:** _pending final metadata commit_ (docs: complete plan)

## Files Created/Modified

- `echo/config.py` — new `resolve_config_path(env)` helper + `CONFIG_PATH = resolve_config_path()`; `Mapping` import added. Writer, loader, corruption handling and secret permissions are untouched.
- `tests/test_config_env_override.py` — 8 tests covering the override and the preserved default, including a real write/read round-trip.

## Decisions Made

- **Pure, injectable resolver** — `resolve_config_path(env=None)` takes an explicit mapping (defaulting to `os.environ`), so tests never mutate the process environment and the module keeps a single, import-time `CONFIG_PATH` attribute that existing monkey-patching tests rely on.
- **Blank override falls back** — an empty/whitespace `ECHO_CONFIG_PATH` resolves to the repository root, so a misconfigured container env var cannot silently relocate the config away from the mounted file.
- **`~` expanded, path not normalized** — `expanduser()` is applied (container/CLI ergonomics) but the path is otherwise preserved verbatim, keeping relative overrides intact.
- **https-only posture untouched** — `validate_base_url` lives in `echo/llm_client.py` and is unchanged; the override only relocates the file (T-09-11).

## Deviations from Plan

**1. [Plan-internal inconsistency — TDD flag] Task 1 is marked `tdd="true"` but the plan assigns test creation to Task 2**

- **Found during:** Task 1 planning/execution.
- **Issue:** Task 1 carries `tdd="true"`, yet the plan's own file split has Task 1 modify only `echo/config.py` and Task 2 create `tests/test_config_env_override.py`. A strict RED-before-GREEN flow would have created the test file during Task 1, making Task 2's "create the test file" step empty and collapsing the intended two-commit structure.
- **Fix:** Followed the plan's explicit task/file structure — Task 1 implemented the source change and verified with its static `<automated>` command; Task 2 added the tests and verified with the quick-tier `unittest` run. The net result is equivalent to TDD (implementation then a passing test suite), with the plan's two atomic commits preserved.
- **Files modified:** same as the plan (`echo/config.py`, `tests/test_config_env_override.py`).
- **Verification:** Task 1 static check passed; Task 2 8/8 OK; full suite 129/129 OK.
- **Committed in:** `6cedcdc` (Task 1) and `15fd274` (Task 2).

---

**Total deviations:** 1 plan-internal inconsistency resolution (no scope or behavior change).
**Impact on plan:** None — the delivered files, commits and outcomes match the plan's declared artifacts and acceptance criteria exactly.

## Issues Encountered

- **No functional issues.** The `_FakeResponse.__del__` `AttributeError` lines printed after the full suite are pre-existing cleanup noise from `test_llm_client.py` mock objects, unrelated to this plan (out of scope per the deviation scope boundary); the suite still reports `OK`.
- The untracked `audio/` directory (`audio_2026-09-21_17-16-50.mp3`) pre-existed this plan and was left untouched — not committed.

## Known Stubs

None — the plan delivered a pure helper plus tests. No placeholder values, hardcoded empties, or unwired data sources were introduced.

## Threat Flags

None — no security-relevant surface beyond the plan's `<threat_model>`. T-09-03 (single-file mount → `os.replace` EBUSY) is mitigated by supporting a **directory** mount with `_atomic_write_secure` unchanged; T-09-10 (attacker-set `ECHO_CONFIG_PATH`) is accepted (set by the container operator at run time, same trust level as the file); T-09-11 (mount bypasses https-only) is mitigated because `validate_base_url` is explicitly untouched and `config.py` never validates or rewrites `base_url`; T-09-12 (API key written to a mounted dir) is mitigated by the unchanged `chmod 0600` owner-only write.

## User Setup Required

None - no external service configuration required. The operator's live API key in the gitignored `app_config.json` was never read, printed, or committed.

## Next Phase Readiness

- **Ready for Plan 09-03** (docs: document the `/config` directory mount + `ECHO_CONFIG_PATH=/config/app_config.json` contract and `docker save`/`load`) and **Plan 09-04** (build + browser E2E, including the mounted-config write round-trip).
- **CNTR-03 core is in place and test-guarded:** the container can now redirect the config to a directory mount while desktop behavior and the https-only endpoint policy are provably unchanged.
- **Residual for verification:** the container-level config write round-trip against a real bind-mounted directory is owned by Plan 09-04 (T-09-03/T-09-06).

---

*Phase: 09-containerized-gui-delivery*
*Completed: 2026-10-01*

## Self-Check: PASSED

- FOUND: echo/config.py
- FOUND: tests/test_config_env_override.py
- FOUND: .planning/phases/09-containerized-gui-delivery/09-02-SUMMARY.md
- FOUND commit: 6cedcdc (Task 1)
- FOUND commit: 15fd274 (Task 2)
- `py -3 -c "...resolve_config_path..."` → OK config override
- `py -3 -m unittest discover -s tests -p "test_config_env_override.py" -v` → Ran 8 tests, OK
- `py -3 -m unittest discover -s tests -v` → Ran 129 tests, OK
