---
phase: 08-supply-chain-hardening
plan: 02
subsystem: infra
tags: [supply-chain, pip-tools, pip-compile, hashes, sha256, cuda, pytorch, torch, requirements-lock, reuse-hashes]

# Dependency graph
requires:
  - phase: 08-supply-chain-hardening
    plan: 01
    provides: "requirements.txt — the pip-compile CPU lock (24 packages, 634 sha256 hashes) used to seed the CUDA lock"
provides:
  - "requirements-cuda.in — hand-written source of truth for the CUDA lock (extra-index line + 4 direct pins)"
  - "requirements-cuda.txt — pip-compile CUDA lock: torch==2.14.0+cu130 with all 24 index-published sha256 hashes, 24 packages, 634 hashes"
  - "proof that the CUDA lock differs from the CPU lock only in the torch pin (version + hash set parity for every other package)"
  - "proof that the locked torch hashes equal the live cu130 index hashes"
affects: [08-03-invariant-test-docs, 08-04-hash-checked-install]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "seed-then-reuse: pre-seed --output-file with the complete desired lock and pass --reuse-hashes so LocalRequirementsRepository.get_hashes short-circuits every lookup (zero wheel downloads)"
    - "second-index locking: --emit-index-url (default on) carries the cu130 extra-index line into the lock; --require-hashes remains the enforcement contract"
    - "index-published hashes from href fragments: match the URL-encoded version 2.14.0%2Bcu130, never the literal 2.14.0+cu130"

key-files:
  created: [requirements-cuda.in, requirements-cuda.txt]
  modified: []

key-decisions:
  - "torch==2.14.0+cu130 is locked from https://download.pytorch.org/whl/cu130 because the +cu130 build is not published on PyPI"
  - "The CUDA lock is a seeded copy of the CPU lock with only the torch block swapped; --reuse-hashes reuses every hash so nothing downloads"
  - "--emit-index-url stays at its default (ON) for this lock so pip install --require-hashes can reach the cu130 wheel (the opposite of Plan 08-01's pure-PyPI --no-emit-index-url)"
  - "CUDA is bundled in the Windows wheel — the dependency closure is identical to the CPU torch build (no nvidia-* packages), which is why both locks share one package set"

patterns-established:
  - "pip-tools --generate-hashes cannot hash a +local wheel from a non-PyPI index without downloading every candidate (allow_all_wheels + missing PyPI JSON entry); seeding the output file bypasses resolve_hashes entirely"
  - "A second lock's trustworthiness is proven by parity: every non-torch package must be identical (version AND hash set) to the CPU lock"

requirements-completed: [SUP-02]

# Metrics
duration: 2min
completed: 2026-09-23
---

# Phase 8 Plan 02: Supply-chain Hardening — CUDA Lock Summary

**CUDA lock pinning `torch==2.14.0+cu130` from the PyTorch cu130 index with all 24 published sha256 hashes, compiled via seed + `--reuse-hashes` with zero CUDA wheel downloads**

## Performance

- **Duration:** ~2 min
- **Started:** 2026-09-23T15:36:44Z
- **Completed:** 2026-09-23T15:38:19Z
- **Tasks:** 3 (2 committed, 1 verification-only)
- **Files modified:** 2 (both created)

## Accomplishments
- `requirements-cuda.in` written: exactly one `--extra-index-url https://download.pytorch.org/whl/cu130` line plus the four direct pins, with `torch==2.14.0+cu130`.
- `requirements-cuda.txt` compiled as a genuine pip-tools output: **24 packages, 634 `--hash=sha256:` lines, 699 lines**, header recording the exact reproducible `--generate-hashes --reuse-hashes` command and **no spurious `--no-index`**.
- `torch==2.14.0+cu130` pinned with **all 24 index-published sha256 hashes**, including the known-good `cp314` `win_amd64` digest `78ab64d12e478c8baedc4d90e662f6ffca2b6cb8a872a02b734a8aa3e00277eb`.
- The compile completed with **exit code 0 and zero wheel downloads** — the seeded output file let `LocalRequirementsRepository.get_hashes` return every hash from disk, so the ~tens-of-GB mass download the research warned about never started.
- Parity proven: every non-`torch` package has the **identical version and identical hash set** in both locks; the two locks differ only in the torch pin.
- Locked torch hashes **equal the live cu130 index hashes** (re-fetched from `https://download.pytorch.org/whl/cu130/torch/`), so a silently rotated or substituted wheel would fail the install.
- Hash-checking mode accepts the file: `pip install --require-hashes --dry-run --no-deps -r <probe>` for `tqdm==4.70.0` reported `Would install tqdm-4.70.0`, exit 0, even with the extra index present.

## Task Commits

Each task was committed atomically:

1. **Task 1: Write requirements-cuda.in and seed requirements-cuda.txt from the CPU lock** — `76cec72` (chore)
2. **Task 2: Compile the CUDA lock with --reuse-hashes** — `53cca4d` (chore)
3. **Task 3: Verify CUDA lock parity with the CPU lock and the index hash** — no commit (`files_modified` intentionally empty; read-only verification plus a transient `A:\pip-tmp\probe_cuda.txt`)

**Plan metadata:** _pending final metadata commit_ (docs: complete plan)

## Files Created/Modified
- `requirements-cuda.in` — created; cu130 extra-index line + `openai-whisper==20250625`, `torch==2.14.0+cu130`, `numpy==2.4.4`, `tqdm==4.70.0` (LF, UTF-8, no BOM)
- `requirements-cuda.txt` — created; pip-compile CUDA lock, 24 packages / 634 hashes / 699 lines, `setuptools==84.0.0` in the trailing unsafe block, torch block carrying the 24 cu130 hashes

## Decisions Made
- The CUDA build must be a **separate lock**: PyPI has no `2.14.0+cu130` release, so the CPU lock's `torch==2.14.0` cannot select it.
- `--emit-index-url` is deliberately **left on** for this lock (unlike Plan 08-01's pure-PyPI locks) so the `--extra-index-url` line reaches `pip install --require-hashes`.
- The seed is the intended lock (only the torch block differs); pip-tools is used as a validator/normalizer, not as a resolver, which is what keeps the run download-free.
- The `# via` provenance annotations were carried into the seed so the post-compile diff is only the header (Task 2 committed 8 insertions / 7 deletions — header only).

## Deviations from Plan

None - plan executed exactly as written.

The seed-and-reuse approach behaved precisely as the research predicted: the seed command printed `seeded hashes: 24`, the compile exited 0 with no `Downloading` lines, and every verification probe passed on the first run.

## Issues Encountered
- `git status --short` reports a persistent ` M .planning/config.json` that predates this plan. The working-tree blob is byte-identical to `HEAD` (`git hash-object` == `git rev-parse HEAD:.planning/config.json` == `8ea7cd3…`), so it is a git stat-cache (mtime) artifact, not a content change. Refreshing the index did not clear it; it is outside this plan's scope and was left untouched.
- pip-tools rewrote the file's leading region on compile (it replaced the carried-over CPU header with its own and inserted one blank line after the extra-index line), which is why the lock grew from 698 to 699 lines. Verified there is exactly one `autogenerated by pip-compile` header and no stale `--output-file requirements.txt requirements.in` line.

## Known Stubs
None — the lock is fully populated with real package pins and real sha256 digests; no placeholder or hardcoded-empty values.

## Threat Flags
None — no new network endpoints, auth paths, file-access patterns, or trust-boundary surface beyond the plan's `<threat_model>`. T-08-03 (tampered cu130 wheel), T-08-11 (dependency confusion via the extra index), T-08-12 (download DoS), T-08-13 (lock divergence), and T-08-14 (untraceable command) are all addressed by this plan's implementation; T-08-15 (install-time build backend) remains accepted as documented.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- `requirements-cuda.txt` is ready for Plan 08-03's invariant test (must pin `torch==2.14.0+cu130` and contain the cu130 extra-index line) and for Plan 08-04's manual CUDA install checkpoint.
- The CUDA lock's package set matches the CPU lock exactly, so Plan 08-03's cross-lock assertions can compare the two without special-casing torch's version.
- Installing `requirements-cuda.txt` is a ~2.8 GB download and stays a `checkpoint:human-verify` in Plan 08-04; it was deliberately not attempted here.
- No blockers.

---
*Phase: 08-supply-chain-hardening*
*Completed: 2026-09-23*

## Self-Check: PASSED

- FOUND: requirements-cuda.in
- FOUND: requirements-cuda.txt
- FOUND: .planning/phases/08-supply-chain-hardening/08-02-SUMMARY.md
- FOUND: 76cec72 (Task 1 commit)
- FOUND: 53cca4d (Task 2 commit)
