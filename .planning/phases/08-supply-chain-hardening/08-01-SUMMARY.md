---
phase: 08-supply-chain-hardening
plan: 01
subsystem: infra
tags: [supply-chain, pip-tools, pip-compile, hashes, requirements-lock, sha256, pyinstaller]

# Dependency graph
requires:
  - phase: 07-security-hardening
    provides: SEC-06 four direct pins (openai-whisper/torch/numpy/tqdm) and the pin-contract test baseline
provides:
  - "requirements.in — hand-written source of truth for the CPU lock (4 direct pins)"
  - "requirements.txt — pip-compile CPU lock, 24 direct+transitive pins, 634 sha256 hashes"
  - "requirements-dev.in — source of truth for the dev-tooling lock"
  - "requirements-dev.txt — pip-compile dev lock (pip-tools/pip-audit/pyinstaller + transitive), 391 sha256 hashes"
  - "proof that --require-hashes rejects a tampered digest (negative control)"
affects: [08-02-cuda-lock, 08-03-invariant-test-docs, 08-04-hash-checked-install]

# Tech tracking
tech-stack:
  added: [pip-tools 7.6.1]
  patterns:
    - "pip-compile --generate-hashes --allow-unsafe --strip-extras --no-emit-index-url --no-emit-trusted-host for pure-PyPI locks"
    - "CUSTOM_COMPILE_COMMAND to record a truthful, reproducible lock header"
    - "negative-control discipline: an invariant is only proven once it is seen to fail"

key-files:
  created: [requirements.in, requirements-dev.in, requirements-dev.txt]
  modified: [requirements.txt]

key-decisions:
  - "torch==2.14.0 carries no +cu130 local tag in the CPU lock (PyPI CPU variant); CUDA is a separate lock owned by 08-02"
  - "--allow-unsafe is mandatory so setuptools (declared by torch) stays in the lock; without it --require-hashes installs fail"
  - "pyinstaller==6.19.0 pinned into the dev lock per user decision; pyinstaller-hooks-contrib pinned transitively, not in the .in file"
  - "SUP-05 is shared: this plan delivers the dev-tooling lock half; the pip-audit guide half lands in 08-03"

patterns-established:
  - "Pure-PyPI --generate-hashes reads digests from the PyPI JSON API — zero wheel downloads"
  - "Negative controls must tamper *every* hash of a requirement; pip accepts a package if any single listed hash matches"

requirements-completed: [SUP-01, SUP-05]

# Metrics
duration: 4min
completed: 2026-09-23
---

# Phase 8 Plan 01: Supply-chain Hardening — CPU + Dev Locks Summary

**pip-tools compiled CPU and dev-tooling locks pinning all 24 direct+transitive runtime packages (634 sha256 hashes) and the dev toolchain (391 hashes), with hash enforcement proven in both directions**

## Performance

- **Duration:** ~4 min
- **Started:** 2026-09-23T15:29:51Z
- **Completed:** 2026-09-23T15:33:34Z
- **Tasks:** 3 (2 committed, 1 verification-only)
- **Files modified:** 4 (3 created, 1 rewritten)

## Accomplishments
- `requirements.txt` converted from a hand-written 4-line pin list into a pip-compile lock: **24 packages, 697 lines, 634 `--hash=sha256:` lines**, closing the transitive-dependency gap (`numba`, `tiktoken`, `requests`, `sympy`, `jinja2`, …).
- `requirements-dev.txt` compiled from `requirements-dev.in` (`pip-tools==7.6.1`, `pip-audit==2.10.1`, `pyinstaller==6.19.0`) with every transitive dep hashed (391 hashes; `pyinstaller-hooks-contrib==2026.7` pinned transitively).
- The four SEC-06 direct pins are unchanged in value; the lock's package set matches the researched set exactly.
- Hash enforcement proven: a good hash is accepted (`Would install tqdm-4.70.0`, exit 0) and a fully tampered digest is rejected (`THESE PACKAGES DO NOT MATCH THE HASHES FROM THE REQUIREMENTS FILE`, exit 1).
- Zero wheel downloads for the pure-PyPI compiles — every digest came from the PyPI JSON API, so the 1.2 GB of free space on `C:` was never at risk.

## Task Commits

Each task was committed atomically:

1. **Task 1: Install pip-tools and write the lock inputs** — `28e1f14` (chore)
2. **Task 2: Compile the CPU lock and the dev lock with hashes** — `3936d4f` (chore)
3. **Task 3: Verify both locks and prove hash enforcement** — no commit (`files_modified` intentionally empty; transient temp files only)

**Plan metadata:** _pending final metadata commit_ (docs: complete plan)

## Files Created/Modified
- `requirements.in` — created; four direct runtime pins (LF, UTF-8, no BOM), no `>=`/`~=`, no `cu130`, no pyinstaller
- `requirements.txt` — rewritten; pip-compile CPU lock, 24 packages / 634 hashes, `setuptools==84.0.0` in the trailing unsafe block
- `requirements-dev.in` — created; `pip-tools==7.6.1`, `pip-audit==2.10.1`, `pyinstaller==6.19.0`
- `requirements-dev.txt` — created; pip-compile dev lock, 391 hashes, `pip==26.2.1` + `setuptools==84.0.0` in the unsafe block

## Decisions Made
- `torch==2.14.0` deliberately has no `+cu130` local tag — the CPU lock is the default PyPI variant; the CUDA variant is Plan 08-02's separate lock.
- `--allow-unsafe` is retained as mandatory: `torch` declares `Requires-Dist: setuptools>=77.0.3`; without the flag pip-tools drops `setuptools` and `--require-hashes` fails.
- `CUSTOM_COMPILE_COMMAND` set for both compiles so each header records an accurate command with no spurious `--no-index`.
- `pyinstaller==6.19.0` is pinned into the dev lock (user decision); `pyinstaller-hooks-contrib` is left out of the `.in` file and pinned transitively.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Negative-control tamper command was mechanically insufficient**
- **Found during:** Task 3 (prove hash enforcement)
- **Issue:** The plan's negative control runs `re.sub(r'--hash=sha256:[0-9a-f]{8}', '--hash=sha256:00000000', t, count=1)`, corrupting only the **first** of `tqdm`'s two listed hashes. pip's hash-checking mode accepts a requirement when **any** listed digest matches, so the second (untampered) hash matched the downloaded wheel and the install *succeeded* (exit 0, `Would install tqdm-4.70.0`) — the control falsely "passed" instead of proving rejection.
- **Fix:** Tampered **all** `--hash=sha256:<64 hex>` values in the probe copy to all-zero, leaving no digest that could match. Re-run then produced the expected `ERROR: THESE PACKAGES DO NOT MATCH THE HASHES FROM THE REQUIREMENTS FILE` with exit code 1.
- **Files modified:** none in the repository (`A:\pip-tmp\probe.txt` / `probe_bad.txt` only, both deleted afterwards)
- **Verification:** Good-hash probe → exit 0 / `Would install tqdm-4.70.0`; all-hashes-tampered probe → exit 1 / `DO NOT MATCH THE HASHES`
- **Committed in:** n/a (verification-only task; no repo change)

---

**Total deviations:** 1 auto-fixed (1 bug — a plan-defective verification command, not a product change)
**Impact on plan:** None on the delivered locks. The fix strengthened the proof (the invariant is now genuinely observed to fail) without touching any committed file.

## Issues Encountered
- `pip-compile` emitted many benign `Cache entry deserialization failed, entry ignored` warnings on the dev-lock run (pip's HTTP cache under the relocated `A:\pip-tmp` temp dir). Compilation still exited 0 with a complete, hashed lock; no wheel downloads occurred.
- Git warned `LF will be replaced by CRLF the next time Git touches it` on add (repo has no `.gitattributes` and `core.autocrlf` is on). Committed blobs are LF as required; the warning is a checkout-time artifact only.

## Known Stubs
None — both locks are fully populated with real package pins and real sha256 digests.

## Threat Flags
None — no new network endpoints, auth paths, or trust-boundary surface beyond the plan's `<threat_model>` (T-08-01/02/07/08/09/10 all covered by this plan's implementation).

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- `requirements.in` / `requirements.txt` are ready to seed Plan 08-02's CUDA lock (`--reuse-hashes` off the CPU lock).
- `requirements-dev.in` / `requirements-dev.txt` are ready for Plan 08-03's invariant-test rewrite and the local `pip-audit` guide.
- The four SEC-06 direct pins are unchanged, so `tests/test_requirements_pinning.py` still encodes its old flat-4-line contract and is expected to fail until Plan 08-03 rewrites it (by design — that file is 08-03's single-owner deliverable).
- No blockers.

---
*Phase: 08-supply-chain-hardening*
*Completed: 2026-09-23*

## Self-Check: PASSED

- FOUND: requirements.in
- FOUND: requirements.txt
- FOUND: requirements-dev.in
- FOUND: requirements-dev.txt
- FOUND: .planning/phases/08-supply-chain-hardening/08-01-SUMMARY.md
- FOUND: 28e1f14 (Task 1 commit)
- FOUND: 3936d4f (Task 2 commit)
