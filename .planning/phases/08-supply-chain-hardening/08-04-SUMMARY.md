---
phase: 08-supply-chain-hardening
plan: 04
subsystem: infra
tags: [supply-chain, require-hashes, pip-audit, clean-venv, cuda, torch, verification, human-verify, sup-03]

# Dependency graph
requires:
  - phase: 08-supply-chain-hardening
    plan: 01
    provides: "requirements.txt — the pip-compile CPU lock (24 packages, 634 sha256 hashes) proven installable here"
  - phase: 08-supply-chain-hardening
    plan: 02
    provides: "requirements-cuda.txt — the cu130 torch lock operator-confirmed installable here"
  - phase: 08-supply-chain-hardening
    plan: 03
    provides: "the 20-test pinning invariant and the documented --require-hashes install commands exercised here"
provides:
  - "proof that requirements.txt installs in a clean venv under --require-hashes (exit 0, no hash mismatch)"
  - "proof that the installed tree matches the lock exactly for all 24 packages, on the CPU torch build (2.14.0, not +cu130)"
  - "pip-audit results for both the CPU and CUDA locks (no known vulnerabilities; torch +cu130 skipped — not on PyPI)"
  - "a green full suite (106 tests OK) after all lock and doc changes"
  - "operator approval that requirements-cuda.txt installs on CUDA-capable hardware (Task 3 human-verify checkpoint)"
affects: [phase-08-verify-work, phase-05-packaging-distribution]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "verification-only plan: files_modified=[] and no per-task commits; the deliverable is evidence, not artifacts"
    - "installability is proven separately from well-formedness: a lock that parses is not a lock that ships"
    - "one blocking human-verify checkpoint for the only step that cannot be automated (a ~2.8 GB CUDA download)"

key-files:
  created: [.planning/phases/08-supply-chain-hardening/08-04-SUMMARY.md]
  modified: []

key-decisions:
  - "No repository file was changed by this plan: files_modified is [] by design and git status stayed clean throughout"
  - "Task 3 (CUDA install) is a human-verify gate, not an automated task, because the cu130 torch wheel is a ~2.8 GB download the operator must control"
  - "The human typed `approved` with no torch.cuda.is_available() value; the approval is recorded as-is and no GPU-visibility value is invented"
  - "pip-audit skipping torch==2.14.0+cu130 is expected and benign: the +cu130 build is not published on PyPI, so there is no advisory index entry to query"

patterns-established:
  - "The final verification plan of a supply-chain phase exercises the enforcement boundary (--require-hashes against a real install), not just the lock's syntax"
  - "Audit advisories are a reportable finding, never a reason for a verification task to edit a lock"

requirements-completed: [SUP-03]

# Metrics
duration: ~1min (resumed bookkeeping; Tasks 1–2 ran in the pre-checkpoint session)
completed: 2026-09-23
---

# Phase 8 Plan 04: Supply-chain Hardening — End-to-End Install Verification Summary

**Proved the locks are installable, not merely well-formed: a clean-venv `--require-hashes` install of `requirements.txt` matched all 24 pins on the CPU torch build, `pip-audit` was clean on both locks, the 106-test suite stayed green, and the operator approved the CUDA lock install on real hardware**

## Performance

- **Duration:** ~1 min for the resumed bookkeeping session; Tasks 1–2 (clean-venv install, audits, full suite) ran in the pre-checkpoint session
- **Started:** 2026-09-23 (Tasks 1–2 pre-checkpoint; Task 3 resolved 2026-09-23T16:03Z)
- **Completed:** 2026-09-23T16:03:17Z
- **Tasks:** 3 (2 auto verification tasks, 1 blocking human-verify checkpoint)
- **Files modified:** 0 in the repository (verification-only plan; `files_modified: []`)

## Accomplishments

- **SUP-03 proven end-to-end.** The documented install command — `pip install --require-hashes -r requirements.txt` — actually works in a fresh venv, which is the difference between a lock that parses and a lock that ships.
- **Task 1 — clean-venv hash-checked CPU install (exit 0):** the install completed with no `DO NOT MATCH THE HASHES` and no `Hashes are required` error. `openai-whisper==20250625` was built from its sdist (as expected — it publishes no wheel), and no `--only-binary :all:` flag was used.
- **Task 1 — exact version parity:** the installed tree matched the lock for **all 24 packages** (`OK installed versions match the lock: 24`). The import probe resolved the app's core imports and confirmed the **CPU** build — `torch.__version__` is `2.14.0`, not `2.14.0+cu130` — and `pip check` reported `No broken requirements found.`
- **Task 2 — audits clean:** `pip_audit -r requirements.txt` and `pip_audit -r requirements-cuda.txt` both reported **No known vulnerabilities found**. The CUDA lock's `--hash=` lines and `--extra-index-url` line do not upset the audit. `torch==2.14.0+cu130` is skipped by pip-audit because it is not on PyPI — expected, not a finding.
- **Task 2 — full suite green:** `py -3 -m unittest discover -s tests -v` reported `Ran 106 tests ... OK`, including all 20 `test_requirements_pinning` tests. This is the phase gate after every lock and doc change.
- **Task 2 — structural sweep and no-source-change check:** all three locks remain pinned + hashed with no `--no-index`; `echo/` and `main.py` show no diff. Phase 8 stayed a data/docs-only phase.
- **Task 3 — operator approval:** the blocking CUDA human-verify checkpoint was resolved with the operator typing **`approved`**.

## Task Commits

This plan has `files_modified: []`, so no per-task commits exist. It contributes a single metadata commit.

1. **Task 1: Install the CPU lock under hash-checking mode in a clean venv** — no commit (verification-only; writes only to `A:\pip-tmp`, outside the repository)
2. **Task 2: Audit both locks and run the full suite** — no commit (read-only verification)
3. **Task 3: Operator confirmation that the CUDA lock installs on real hardware** — no commit (human-verify checkpoint; no repository file written)

**Plan metadata:** _pending final metadata commit_ (docs: complete plan)

## Files Created/Modified

- `.planning/phases/08-supply-chain-hardening/08-04-SUMMARY.md` — this summary (the plan's only repository artifact)
- No source, lock, test, or documentation file was created or modified by this plan.

## Decisions Made

- **No lock was edited.** Tasks 1 and 2 explicitly prohibit "fixing" a lock to make verification pass; none needed fixing. Had a hash mismatch or a missing wheel surfaced, it would have been recorded as a finding instead (T-08-21).
- **The CUDA install stayed a blocking human-verify checkpoint.** A ~2.8 GB download is not an automated step on the operator's connection (T-08-24); the operator chooses when it runs and deletes the scratch venv afterwards.
- **The approval is recorded without inventing a `torch.cuda.is_available()` value.** The operator typed `approved` and supplied no value, so none is asserted here. The plan explicitly allows `False` on a machine without a usable NVIDIA GPU as an acceptable *install* verification result — the hash verification, not GPU visibility, is the requirement under test.

## Deviations from Plan

None - plan executed exactly as written.

Tasks 1–2 passed on the recorded runs (clean-venv install exit 0 with exact parity, both audits clean, 106/106 suite green), and Task 3 resolved with the operator's `approved` signal. The only nuance is that the operator's resume signal carried no `torch.cuda.is_available()` value; this is recorded honestly rather than back-filled.

## Human Verification Record (Task 3)

**Checkpoint type:** `checkpoint:human-verify` (blocking)
**Resolution:** operator typed **`approved`**

| Plan acceptance item | Status |
|----------------------|--------|
| `PRE_CHECKPOINT_OK` printed before the manual steps | ✅ Re-confirmed on resume (`PRE_CHECKPOINT_OK`) |
| Scratch venv install of `requirements-cuda.txt` under `--require-hashes` completed with exit code 0 | ✅ Confirmed by operator approval |
| Install output contained no `DO NOT MATCH THE HASHES` error | ✅ Confirmed by operator approval |
| `torch.__version__` is exactly `2.14.0+cu130` | ✅ Confirmed by operator approval |
| Observed `torch.cuda.is_available()` value recorded in the resume signal | ⚠️ **No value was provided.** The operator typed `approved` only; no GPU-visibility value is recorded or invented |
| Scratch venv at `A:\pip-tmp\venv-cuda-check` deleted | ✅ Confirmed by operator approval |
| The three new README sections read correctly | ✅ Confirmed by operator approval |

**Note:** The CUDA approval is a named attestation by the operator, consistent with the Phase 6 `06-06` and Phase 7 `07-04` checkpoint precedent. No automated re-run of the ~2.8 GB install was performed (explicitly out of scope on resume).

## Issues Encountered

None - the plan's verification steps behaved as predicted. The `torch==2.14.0+cu130` skip in `pip-audit` is documented above as expected behavior, not a problem.

## Known Stubs

None — this plan created no code, tests, or UI. There are no placeholder values, hardcoded empties, or unwired data sources.

## Threat Flags

None — no new network endpoints, auth paths, file-access patterns, or trust-boundary surface beyond the plan's `<threat_model>`. T-08-05 (a lock that cannot install) is mitigated by the clean-venv CPU install and the operator-confirmed CUDA install; T-08-21 (a verification task patching a broken lock) is mitigated by the no-lock-edit rule, which was not needed; T-08-23 (`app_config.json` disclosure) is mitigated — no probe read the config; T-08-24 (CUDA download DoS) is mitigated by the blocking checkpoint; T-08-25 (vulnerable transitive dep) is mitigated by running pip-audit against both locks.

## User Setup Required

None - no external service configuration required. (The operator's live API key in the gitignored `app_config.json` was never read, printed, or committed.)

## Next Phase Readiness

- **Phase 8 is complete at the plan level:** all four plans (08-01 CPU/dev locks, 08-02 CUDA lock, 08-03 invariant test + docs, 08-04 end-to-end install verification) have been executed, and SUP-01…SUP-05 are complete.
- **SUP-03 is now genuinely proven:** installation via `pip install --require-hashes -r <lockfile>` is documented *and works* in a clean environment, and the CUDA lock is operator-confirmed installable.
- **Ready for `/gsd-verify-work`:** the full suite is 106/106 green, both locks audit clean, and no application source changed in this phase.
- **No blockers.** The only residual item is the accepted T-08-22 risk (unhashed PEP 517 build backend during the `openai-whisper` sdist build), which is documented in the README and carried in the plan's threat register.

---

*Phase: 08-supply-chain-hardening*
*Completed: 2026-09-23*

## Self-Check: PASSED

- FOUND: .planning/phases/08-supply-chain-hardening/08-04-SUMMARY.md
- FOUND: requirements.txt (Task 1 artifact under test)
- FOUND: requirements-cuda.txt (Task 3 artifact under test)
- PRE_CHECKPOINT_OK (Task 3 automated pre-check on resume)
- Clean working tree (git status --short empty; echo/ and main.py show no diff)
