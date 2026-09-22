---
phase: 07-security-hardening
plan: 02
subsystem: config
tags: [config, atomic-write, icacls, chmod, secrets, dependency-pinning, unittest]

# Dependency graph
requires:
  - phase: 06-package-refactor
    provides: echo/config.py with CONFIG_PATH re-anchored to the repository root (REFR-03), DEFAULT_CONFIG shape
provides:
  - "echo/config.py: _atomic_write_secure + _restrict_windows_acl + CONFIG_FILE_MODE 0o600 (SEC-01)"
  - "echo/config.py: ConfigCorruptError(path, detail) raised by load_config on any unusable existing file (SEC-04)"
  - "requirements.txt pinned to openai-whisper==20250625, torch==2.14.0, numpy==2.4.4, tqdm==4.70.0 with srt removed (SEC-06)"
  - "durable tests/test_config_write.py, test_config_read.py, test_requirements_pinning.py"
affects: [07-03, 07-04]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Write-temp-fsync-rename for a secret file: tempfile.mkstemp in the target directory, flush + os.fsync, os.chmod, os.replace, then best-effort ACL"
    - "Non-fatal platform hardening: chmod wrapped so an OSError cannot lose the key; icacls call bounded by timeout=10 with CREATE_NO_WINDOW and every exception swallowed"
    - "Typed corruption reporting: FileNotFoundError -> defaults, everything else -> ConfigCorruptError(path, detail)"
    - "Pin to the verified installed version (numpy 2.4.4), not an unmet upstream floor"

key-files:
  created:
    - tests/test_config_write.py
    - tests/test_config_read.py
    - tests/test_requirements_pinning.py
  modified:
    - echo/config.py
    - requirements.txt
    - README.md
    - SETUP_GUIDE.txt

key-decisions:
  - "Kept the plan's echo/config.py read/write implementations byte-for-byte; no deviations were needed"
  - "numpy pinned DOWN to 2.4.4 (the installed, working version) instead of the old unmet >=2.5.0 floor"
  - "torch pinned as 2.14.0 (not 2.14.0+cu130) so pip install -r requirements.txt works on the default index"
  - "DEFAULT_CONFIG deep-copied on every load and merged['llm'] built with a dict literal, so no caller can alias the module defaults"
  - "ConfigCorruptError(RuntimeError) with explicit path and detail attributes, exported for plan 07-03 to surface in the UI"

patterns-established:
  - "Pattern: _atomic_write_secure(path, text, mode=CONFIG_FILE_MODE) — atomic, owner-only, deletes the temp file on any failure before the rename"
  - "Pattern: per-task unittest modules under tests/ with CONFIG_PATH monkeypatched to a TemporaryDirectory (never the live app_config.json)"

requirements-completed: [SEC-01, SEC-04, SEC-06]

# Metrics
duration: 3min
completed: 2026-09-22
---

# Phase 7 Plan 2: Config-At-Rest Hardening Summary

**Atomic owner-only config writes (mkstemp + fsync + os.replace + icacls) and typed ConfigCorruptError reporting, plus a fully pinned dependency set with the unused srt package removed and both docs made truthful**

## Performance

- **Duration:** 3 min
- **Started:** 2026-09-22T08:45:41Z
- **Completed:** 2026-09-22T08:48:10Z
- **Tasks:** 3
- **Files modified:** 7 (4 modified, 3 created)

## Accomplishments

- `save_config` no longer truncates the live file: it writes a `tempfile.mkstemp` temp file in the config directory, `flush`es + `os.fsync`es, requests `0o600`, and swaps it in with `os.replace`. A failure before the rename leaves the previous config byte-identical and deletes the temp file — no partially written API key can ever exist.
- `0600` is requested on the temp file, and on Windows — where `os.chmod(0o600)` is verifiably a no-op (`st_mode` stays `0o666`) — a best-effort `icacls /inheritance:r /grant:r "<user>:F"` drops inherited ACEs. The ACL step is non-fatal by design: a missing `icacls`, a non-NTFS volume or a locked-down policy cannot abort the save.
- `load_config` now distinguishes "no file yet" (defaults) from "file exists but is unusable" (`ConfigCorruptError` naming the path). Truncated JSON, an array root, a non-object `llm` section and invalid UTF-8 all raise the typed error instead of a bare `AttributeError` or a silent default fallback; the returned structure is deep-copied so `DEFAULT_CONFIG` can no longer be aliased.
- `requirements.txt` is fully pinned (`openai-whisper==20250625`, `torch==2.14.0`, `numpy==2.4.4`, `tqdm==4.70.0`) and the unused `srt` package is gone; `README.md` and `SETUP_GUIDE.txt` no longer claim it is declared while still documenting the project's own `echo/srt.py`.

## Task Commits

Each task was committed atomically (TDD tasks: test → feat):

1. **Task 1: SEC-01 atomic owner-only save_config** - `db30896` (test, RED) → `b6ede54` (feat, GREEN)
2. **Task 2: SEC-04 ConfigCorruptError reporting** - `b133376` (test, RED) → `d9b27b3` (feat, GREEN)
3. **Task 3: SEC-06 dependency pins + docs + tests** - `3b0a7d1` (fix)

**Plan metadata:** (docs: complete config-at-rest hardening plan) — recorded by the final metadata commit

## Files Created/Modified

- `echo/config.py` - Rewritten read/write pair: added `CONFIG_FILE_MODE`, `_restrict_windows_acl`, `_atomic_write_secure`, `ConfigCorruptError`; `load_config` validates shape and raises; `save_config` merges `DEFAULT_CONFIG` then writes atomically. `CONFIG_PATH` and `DEFAULT_CONFIG` are byte-identical to before (REFR-03 preserved).
- `tests/test_config_write.py` - 13 tests: valid JSON, defaults merge, no `.tmp` residue, idempotency, two forced `os.replace`-failure scenarios, `0600` requested, chmod-failure survival, three ACL failure-tolerance cases, the real Windows `(I)`-free assertion, UTF-8 + trailing newline.
- `tests/test_config_read.py` - 12 tests: defaults on missing file, no aliasing, truncated JSON, array root, wrong-typed `llm`, invalid UTF-8, unreadable file, message names the file, never-returns-defaults, partial merge, unknown keys preserved, save/load round trip.
- `tests/test_requirements_pinning.py` - 7 tests: every entry an exact pin, exact expected pin set, `srt` gone, pins match installed versions, README drops the stale claims, SETUP_GUIDE drops the stale section, README still documents `echo/srt.py`.
- `requirements.txt` - 5 lines → 4 exact pins, no `srt`.
- `README.md` - Removed the `srt` tech-stack row and the "declared, but unused" paragraph; noted the exact pins on the requirements line.
- `SETUP_GUIDE.txt` - Section 4.4 renamed to "ПИНЫ ВЕРСИЙ И УДАЛЕНИЕ srt" with the pin list and the `echo/srt.py: build_srt_content` fact.

## Decisions Made

- The plan (`<action>`) was implemented exactly as written, including the new trailing `"\n"` in the saved JSON, which makes byte-comparison tests deterministic.
- `numpy` was pinned **down** to `2.4.4`: the old `>=2.5.0` floor was already unmet by the working install, and SEC-06's point is to pin the verified version, not re-advertise a broken floor.
- `torch==2.14.0` (no `+cu130`): the local tag comes from the PyTorch CUDA wheel index, so pinning it would break installs using the default PyPI index while not changing which wheel is used here.
- `ConfigCorruptError` derives from `RuntimeError` (not `ValueError`/`SummaryApiError`) and carries `path` + `detail`, matching the contract plan 07-03 consumes.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

- The machine's `USERNAME` is Cyrillic (`Тимофей`). Probed before implementing: `icacls <file> /inheritance:r /grant:r "Тимофей:F"` exits 0 and leaves only `NewIron\Тимофей:(F)` (no `(I)`), and the suite's real-`icacls` assertion passes under `text=True` decoding (cp1251). No code change was required.
- The full phase suite emits the benign, already-documented `_FakeResponse` deallocator message from 07-01's `tests/test_llm_client.py` at interpreter shutdown; `Ran 71 tests / OK`, exit code 0, left as-is.

## Self-Check: PASSED

- Files created/modified all exist on disk: echo/config.py, requirements.txt, README.md, SETUP_GUIDE.txt, tests/test_config_write.py, tests/test_config_read.py, tests/test_requirements_pinning.py, 07-02-SUMMARY.md
- Commits verified present: db30896, b6ede54, b133376, d9b27b3, 3b0a7d1

## Stub Tracking

None. No stub patterns (hardcoded empty values flowing to UI, placeholder text, unwired data sources) were introduced — the change is config read/write, dependency pins and docs.

## Threat Flags

None beyond the plan's `<threat_model>`. Every new surface (`app_config.json` permissions, the atomic write path, the `load_config` fallback, `requirements.txt` pinning, the `icacls` subprocess) is already registered as T-07-02-01…T-07-02-08.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- `ConfigCorruptError` is exported exactly as plan 07-03 expects (`from echo.config import ConfigCorruptError`) with `path` and `detail` attributes; plan 07-03 catches it in `SummarizationEngine.__init__` and surfaces it in the UI.
- `load_config()`/`save_config()` signatures and merge semantics are unchanged, so `echo/summarization_engine.py` and `echo/ui/settings_dialog.py` keep working unchanged.
- REFR-03 confirmed: the real `app_config.json` is byte-identical before and after the whole suite (sha256 prefix `bd409a7290c56008`); `CONFIG_PATH` still anchors to the repository root.
- Full phase suite `py -3 -m unittest discover -s tests -v` → 71 tests, OK, exit 0.

---
*Phase: 07-security-hardening*
*Completed: 2026-09-22*
