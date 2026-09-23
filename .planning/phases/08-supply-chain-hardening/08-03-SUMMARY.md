---
phase: 08-supply-chain-hardening
plan: 03
subsystem: testing
tags: [supply-chain, requirements-lock, sha256, require-hashes, pip-audit, pip-tools, cuda, unittest, docs]

# Dependency graph
requires:
  - phase: 08-supply-chain-hardening
    plan: 01
    provides: "requirements.txt (CPU lock, 24 packages / 634 hashes) and requirements-dev.txt (dev-tooling lock) that the rewritten invariant test parses"
  - phase: 08-supply-chain-hardening
    plan: 02
    provides: "requirements-cuda.txt (torch==2.14.0+cu130, 24 packages / 634 hashes) that the CUDA parity assertions compare against the CPU lock"
provides:
  - "tests/test_requirements_pinning.py — rewritten pip-compile lock invariant test, 20 tests, non-vacuous (two mutation controls prove it fails)"
  - "README.md — hash-checked install for CPU/CUDA/dev locks, lock-regeneration guide, local pip-audit workflow"
  - "SETUP_GUIDE.txt — Russian section 4 updated for the hashed locks (4.4 pins+hashes, 4.5 pip-audit)"
affects: [08-04-hash-checked-install]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "parse pip-compile lock syntax with anchored regexes (REQUIREMENT_RE / HASH_RE) into {name: (version, hashes)}"
    - "anti-vacuity guard: assert parsed requirement count == declared-line count so a silently dropped line shape fails loudly"
    - "non-vacuity proof by monkey-patching the module's lock path to a tampered copy and asserting the test now fails (no repo file touched)"

key-files:
  created: []
  modified: [tests/test_requirements_pinning.py, README.md, SETUP_GUIDE.txt]

key-decisions:
  - "The old flat-4-line contract is replaced wholesale: it kept --hash= continuation lines as requirements and dict(line.split('==')) produced 3-element entries on hashed lines, so it could never parse the new lock"
  - "test_pins_match_the_installed_versions is scoped to the four DIRECT deps only (transitive pins float above installed versions: typing-extensions 4.15.0→4.16.0, urllib3 2.7.0→2.8.0, setuptools 82.0.1→84.0.0)"
  - "installed.split('+')[0] keeps the torch check valid on this CUDA machine (installed 2.14.0+cu130 vs CPU lock 2.14.0)"
  - "No test reads app_config.json (operator's live API key, gitignored) — the module reads only the three locks, three .in files and two docs"
  - "Docs keep the echo/srt.py mention and never re-assert an srt dependency: the three preserved SEC-06 assertions still hold"
  - "Both doc files are UTF-8 with CRLF-only endings; every edit preserved CRLF and the plan's Python normalizer was run as a final no-op check"

patterns-established:
  - "A lock file with no durable test silently rots; the invariant test is the enforcement boundary for future contributors"
  - "An invariant is only proven once observed to fail — the plan's two mutation controls (stripped hashes; diverged CUDA numpy) are part of the deliverable's verification"

requirements-completed: [SUP-03, SUP-04, SUP-05]

# Metrics
duration: 3min
completed: 2026-09-23
---

# Phase 8 Plan 03: Supply-chain Hardening — Invariant Test and Docs Summary

**Rewrote `tests/test_requirements_pinning.py` into a 20-test pip-compile lock contract (proven non-vacuous by two mutation controls) and documented the `--require-hashes` install for the CPU/CUDA/dev locks plus a local `pip-audit` workflow**

## Performance

- **Duration:** ~3 min
- **Started:** 2026-09-23T15:40:16Z
- **Completed:** 2026-09-23T15:43:38Z
- **Tasks:** 3 (2 committed, 1 verification-only)
- **Files modified:** 3 (1 rewritten, 2 surgically edited)

## Accomplishments
- `tests/test_requirements_pinning.py` rewritten from a 62-line flat-4-line-pin module into a **20-test** lock contract that parses real pip-compile syntax: `LockFileContractTests` (12) + `DocumentationTests` (8).
- The new module treats all three locks as hashed locks: every requirement must be pinned **and** carry a sha256 hash, no requirement line may be silently skipped, the CUDA lock must pin `torch==2.14.0+cu130` with exactly one cu130 index line and otherwise match the CPU lock byte-for-byte, the dev lock must pin `pip-tools`/`pip-audit`/`pyinstaller==6.19.0`, and no lock may declare `srt`.
- Documentation now teaches hash verification by default: `pip install --require-hashes -r requirements.txt` (CPU) and `-r requirements-cuda.txt` (CUDA), plus the dev-only `requirements-dev.txt`, in both `README.md` and `SETUP_GUIDE.txt`.
- Added a README "Regenerating the locks" section (including the CUDA seed + `--reuse-hashes` requirement that avoids the multi-GB mass download) and a "Dependency audit (pip-audit)" section marked **without CI**; added SETUP_GUIDE subsection 4.5 for the same local audit.
- **Non-vacuity proven:** stripping `--hash=` lines from a copy of the CPU lock makes the hash test fail with **24 failures** (one per package); adding a bogus hash to `numpy` in a copy of the CUDA lock makes the parity test fail with **1 failure**. Neither probe modified a repository file.
- Full suite: **106 tests, OK** (baseline 93; this plan's module contributes 20), ran in ~10.6 s.

## Task Commits

Each task was committed atomically:

1. **Task 1: Rewrite the pinning invariant test to the hashed-lock contract** — `c09d6af` (test)
2. **Task 2: Document the hash-checked install, CUDA lock, dev lock and pip-audit** — `bf4f415` (docs)
3. **Task 3: Prove the full suite is green and the new test is not vacuous** — no commit (`files_modified` intentionally empty; read-only verification plus throwaway copies under `A:\pip-tmp`)

**Plan metadata:** _pending final metadata commit_ (docs: complete plan)

## Files Created/Modified
- `tests/test_requirements_pinning.py` — rewritten; LF, UTF-8, no BOM, trailing newline. `parse_lock()` + `LockFileContractTests` (12) + `DocumentationTests` (8). No `pytest`; no `app_config.json` access.
- `README.md` — Installation step 3 replaced with `--require-hashes` for CPU/CUDA and the dev lock; new "### Regenerating the locks" and "## Dependency audit (pip-audit)" sections before `## Run`; Tech Stack sentence updated to describe the pip-tools lock. `echo/srt.py` mention preserved. UTF-8, CRLF-only (520 CRLF, 0 bare LF).
- `SETUP_GUIDE.txt` — section 4 install block replaced with hash-checked CPU/CUDA/dev commands; 4.4 rewritten to "ПИНЫ ВЕРСИЙ И ХЭШИ (LOCK-ФАЙЛЫ)" (lists `pyinstaller` among the dev lock); new 4.5 pip-audit subsection. No `4.4 srt`. UTF-8, CRLF-only (658 CRLF, 0 bare LF).

## Decisions Made
- Replaced the old module wholesale rather than patching it: its `setUp` kept `--hash=` continuation lines as "requirements", so `assertIn("==", line)` blew up, and `dict(line.split("=="))` produced 3-element entries on hashed lines. Neither failure mode is salvageable.
- Scoped the installed-version assertion to the **four direct deps** because the new lock floats transitive pins above what is installed (`typing-extensions` 4.15.0 → 4.16.0, `urllib3` 2.7.0 → 2.8.0, `setuptools` 82.0.1 → 84.0.0); an all-pins assertion would be unpassable.
- Kept the three SEC-06 doc assertions (`echo/srt.py` present, no `declared, but unused`, no `| srt `, no `4.4 srt`) intact and ensured the doc edits do not reintroduce them.
- TDD ordering held throughout: the 5 doc tests were RED after Task 1 and GREEN after Task 2, exactly as the plan predicted.

## Deviations from Plan

None - plan executed exactly as written.

The five documentation assertions were RED after Task 1 and GREEN after Task 2 as predicted; the two mutation controls produced the expected 24 and 1 failures on the first run; the CRLF normalization step was a verified no-op (the edit tool preserved CRLF on every edit).

## Issues Encountered
- The `edit` tool matched CRLF-terminated lines with LF `oldString` input and re-inserted multi-line replacements as CRLF, so no mixed endings were ever introduced; the plan's normalizer confirmed **0** bare LF in both files.
- Git printed the usual `LF will be replaced by CRLF` warning when staging `tests/test_requirements_pinning.py` (no `.gitattributes`, `core.autocrlf` on). The committed blob is LF as intended; the warning is a checkout-time artifact only (same as Plan 08-01).
- Mutation controls wrote their temporary tampered lock copies under `A:\pip-tmp` (set `TMP`/`TEMP`) to respect the ~1.1 GB free on `C:`; both directories were transient and outside the repository.

## Known Stubs
None — the test module, README and SETUP_GUIDE contain no placeholder values, no TODO/FIXME, and the test asserts against real lock/doc content. No hardcoded-empty values flow to any output.

## Threat Flags
None — no new network endpoints, auth paths, or trust-boundary surface beyond the plan's `<threat_model>`. T-08-04 (docs instructing a non-hash-checked install), T-08-16 (lock regression with no test), T-08-17 (parser silently skipping malformed lines), T-08-18 (a test reading `app_config.json`), T-08-19 (CUDA regen without `--reuse-hashes`) and T-08-20 (mixed/lost encodings) are all mitigated by this plan's implementation and proven by the Task 3 probes.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Plan 08-04 (hash-checked install) now has a green invariant test and a documented, hash-checked install command for both the CPU lock and the CUDA lock.
- All five previously-RED doc assertions pass; the suite is 106/106 green, so Plan 08-04's checkpoint starts from a clean baseline.
- Installing `requirements-cuda.txt` remains a ~2.8 GB download and is still a `checkpoint:human-verify` in Plan 08-04; it was deliberately not attempted here (disk rule).
- No blockers.

---
*Phase: 08-supply-chain-hardening*
*Completed: 2026-09-23*

## Self-Check: PASSED

- FOUND: tests/test_requirements_pinning.py
- FOUND: README.md
- FOUND: SETUP_GUIDE.txt
- FOUND: .planning/phases/08-supply-chain-hardening/08-03-SUMMARY.md
- FOUND: c09d6af (Task 1 commit)
- FOUND: bf4f415 (Task 2 commit)
