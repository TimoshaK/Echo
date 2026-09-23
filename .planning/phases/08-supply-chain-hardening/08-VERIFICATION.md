---
phase: 08-supply-chain-hardening
verified: 2026-09-23T23:08:11Z
status: human_needed
score: 5/5 must-haves verified
re_verification: false
gaps: []
human_verification:
  - test: "Confirm the CUDA lock installs on CUDA-capable hardware and capture the GPU-visibility value"
    expected: "In a scratch venv: `py -3 -m pip install --require-hashes -r requirements-cuda.txt` exits 0 with no hash mismatch; `import torch; print(torch.__version__, torch.cuda.is_available())` prints `2.14.0+cu130 True` on a machine with a usable NVIDIA GPU (False is acceptable for install verification on a non-GPU machine)."
    why_human: "The cu130 torch wheel is a ~2.8 GB download and cannot be run as an automated step. The 08-04 Task 3 blocking checkpoint was resolved with the operator typing `approved`, but the resume signal carried no `torch.cuda.is_available()` value, so the GPU-visibility half of the claim is an operator attestation, not a machine-captured result."
---

# Phase 8: Supply-chain hardening Verification Report

**Phase Goal:** Make the dependency tree fully reproducible and tamper-evident — every direct and transitive package pinned with hashes, for both CPU and CUDA torch variants, without CI
**Verified:** 2026-09-23T23:08:11Z
**Status:** human_needed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
| --- | ----- | ------ | -------- |
| 1 | A pip-tools compiled lock (`requirements.txt`) pins ALL transitive dependencies with `--generate-hashes` (CPU/default torch) | ✓ VERIFIED | `requirements.txt`: 697 lines, **24 packages**, **634** `--hash=sha256:` lines, header records `pip-compile --generate-hashes --allow-unsafe --strip-extras --no-emit-index-url --no-emit-trusted-host ...`. Includes the transitive closure (`numba`, `llvmlite`, `tiktoken`, `sympy`, `jinja2`, `requests`, `setuptools==84.0.0`, …). Every requirement line ends in `\` and is immediately followed by a `--hash=sha256:` line (0 violations). No `--no-index`. `requirements.in` (runtime) holds exactly the 4 direct pins and contains **no** `pyinstaller`, no `>=`/`~=`, no `cu130`. |
| 2 | A separate CUDA lock (`requirements-cuda.txt`) pins `torch==2.14.0+cu130` via the PyTorch cu130 index, with hashes | ✓ VERIFIED | `requirements-cuda.txt`: 24 packages, 634 hashes. Exactly **one** `--extra-index-url https://download.pytorch.org/whl/cu130`. `torch==2.14.0+cu130 \` present (CPU pin `torch==2.14.0 \` absent) with **24 hashes** that equal the **live** index set re-fetched this session (24/24 equal, incl. the known `cp314-win_amd64` digest `78ab64d1…`). All 23 non-torch packages are identical (version **and** hash set) to the CPU lock. Header records `--generate-hashes --reuse-hashes`; no `--no-index`. |
| 3 | Installation is documented and works via `pip install --require-hashes -r <lockfile>` | ✓ VERIFIED | Documented for both locks in `README.md` (`### 3. Install dependencies` → `--require-hashes -r requirements.txt` and `-r requirements-cuda.txt`) and `SETUP_GUIDE.txt` (section 4). Mechanism independently reproduced: `pip install --require-hashes --dry-run --no-deps -r <tqdm block>` → `Would install tqdm-4.70.0`, exit 0; tampered copy → exit 1, `Expected sha256 000…0 / Got 7f585706…`. Clean-venv CPU install (exit 0, all 24 pins matched, `torch 2.14.0`) is recorded in 08-04 (not re-run here — heavy). CUDA real-hardware install is operator-attested (see Human Verification). |
| 4 | The pinning invariant test (`tests/test_requirements_pinning.py`) is updated to the new contract and passes | ✓ VERIFIED | Rewritten to `parse_lock()` + `LockFileContractTests` (12) + `DocumentationTests` (8) = **20 tests**. Full suite re-run this session: **`Ran 106 tests … OK`** (baseline 93). Non-vacuity independently reproduced: stripping `--hash=` from a temp copy of the CPU lock → **24 failures**; injecting a bogus `numpy` hash into a temp copy of the CUDA lock → **1 failure**. Module does not import `pytest` and never references `app_config.json`. |
| 5 | A local `pip-audit` guide is documented (no CI); dev-only tooling lives in a separate `requirements-dev` lock | ✓ VERIFIED | `README.md` `## Dependency audit (pip-audit)` and `SETUP_GUIDE.txt` `4.5` both document the local, operator-run workflow explicitly marked "без CI / без CI". **No CI configuration exists** (no `.github/`, no `.gitlab-ci.yml`). `requirements-dev.txt` is a real hashed lock: **40 packages**, 391 hashes, pins `pip-tools==7.6.1`, `pip-audit==2.10.1`, `pyinstaller==6.19.0` (and transitively `pyinstaller-hooks-contrib`), no `--no-index`. Docs list `pyinstaller` among the dev-lock contents. |

**Score:** 5/5 must-haves verified

### Required Artifacts

| Artifact | Expected | Status | Details |
| -------- | -------- | ------ | ------- |
| `requirements.in` | Source of truth for the CPU lock (4 direct pins) | ✓ VERIFIED | 4 exact pins; no `pyinstaller`/`cu130`/`>=`/`~=` |
| `requirements.txt` | pip-tools compiled CPU lock with hashes | ✓ VERIFIED | 24 pkgs / 634 hashes / 697 lines; accurate header; `setuptools==84.0.0` in unsafe block |
| `requirements-dev.in` | Source of truth for the dev-tooling lock | ✓ VERIFIED | `pip-tools==7.6.1`, `pip-audit==2.10.1`, `pyinstaller==6.19.0`; no `pyinstaller-hooks-contrib` |
| `requirements-dev.txt` | pip-tools compiled dev lock with hashes | ✓ VERIFIED | 40 pkgs / 391 hashes; header present; no `--no-index` |
| `requirements-cuda.in` | Source of truth for the CUDA lock | ✓ VERIFIED | one `--extra-index-url …/cu130` + 4 direct pins with `torch==2.14.0+cu130` |
| `requirements-cuda.txt` | pip-tools compiled CUDA lock with hashes | ✓ VERIFIED | 24 pkgs / 634 hashes / 699 lines; cu130 index line exactly once; torch 24 hashes match live index |
| `tests/test_requirements_pinning.py` | Durable invariant tests, ≥150 lines, contains `def parse_lock(` | ✓ VERIFIED | 169 lines; `parse_lock()` present; 20 tests; non-vacuous |
| `README.md` | Hash-checked install instructions, regen guide, pip-audit guide | ✓ VERIFIED | Contains `--require-hashes`, both lock names, `pip-audit`, `pyinstaller`, `--reuse-hashes`; retains `echo/srt.py`; CRLF-only |
| `SETUP_GUIDE.txt` | Russian setup guide updated for hashed locks and pip-audit | ✓ VERIFIED | Contains `--require-hashes`, both lock names, `pip_audit`, `pyinstaller`; `4.4 srt` absent; CRLF-only |

### Key Link Verification

| From | To | Via | Status | Details |
| ---- | -- | --- | ------ | ------- |
| `requirements.in` | `requirements.txt` | `pip-compile --generate-hashes` | ✓ WIRED | Header line 5 records the exact CPU compile command |
| `requirements-dev.in` | `requirements-dev.txt` | `pip-compile --generate-hashes` | ✓ WIRED | Header records the exact dev compile command |
| `requirements-cuda.in` | `requirements-cuda.txt` | `pip-compile --generate-hashes --reuse-hashes` | ✓ WIRED | Header records the seed + reuse command; cu130 index line emitted |
| `tests/test_requirements_pinning.py` | `requirements.txt` / `requirements-cuda.txt` / `requirements-dev.txt` | `parse_lock(...)` | ✓ WIRED | Module reads and parses all three locks; asserts pin+hash, parity, headers |
| `README.md` / `SETUP_GUIDE.txt` | `requirements.txt` / `requirements-cuda.txt` | documented `--require-hashes -r …` | ✓ WIRED | Both commands present in both docs; mechanism reproduced |

### Data-Flow Trace (Level 4)

Not applicable — this phase produces static lock data files and documentation. There is no component rendering dynamic runtime data, so there is no upstream data source to trace. The equivalent "data flow" check (locked digests == live index digests) was performed and passed (24/24).

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
| -------- | ------- | ------ | ------ |
| Full test suite is green | `py -3 -m unittest discover -s tests -v` | `Ran 106 tests … OK` | ✓ PASS |
| Hash-checking accepts a good lock entry | `pip install --require-hashes --dry-run --no-deps -r <tqdm block>` | `Would install tqdm-4.70.0`, exit 0 | ✓ PASS |
| Hash-checking rejects a tampered digest | same, all hashes zeroed | exit 1, `Expected sha256 000… / Got 7f585706…` | ✓ PASS |
| Invariant test is non-vacuous (hash removal) | monkey-patched temp CPU lock | 24 failures | ✓ PASS |
| Invariant test is non-vacuous (CUDA parity) | monkey-patched temp CUDA lock | 1 failure | ✓ PASS |
| Locked torch hashes match the live cu130 index | re-fetch `…/whl/cu130/torch/` | 24 live == 24 locked | ✓ PASS |
| Structural sweep: every requirement hashed, no `--no-index` | inline probe over all three locks | CPU 24/634, CUDA 24/634, DEV 40/391, 0 violations | ✓ PASS |
| `pip-audit` reports no vulnerabilities | `py -3 -m pip_audit -r requirements.txt` | **SKIP** — `No module named pip_audit` in the current interpreter | ? SKIP |
| Clean-venv CPU install | `pip install --require-hashes -r requirements.txt` in a fresh venv | Not re-run (heavy ~200 MB); attested exit 0 in 08-04 | ? SKIP |

*The `pip-audit` skip is not a gap: `SUP-05` requires the guide + the dev lock (both present and hashed). The guide's own first step installs `requirements-dev.txt`, which provides `pip_audit`; the tool is simply not installed in the current interpreter, so the 08-04 "No known vulnerabilities found" result is attested rather than independently reproduced here.*

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
| ----------- | ----------- | ----------- | ------ | -------- |
| SUP-01 | 08-01 | CPU lock of transitive deps with hashes (`--generate-hashes`) | ✓ SATISFIED | `requirements.txt` 24 pkgs / 634 hashes / accurate header; no `--no-index`; runtime `.in` has 4 direct pins and no `pyinstaller` |
| SUP-02 | 08-02 | Separate CUDA lock (`torch==2.14.0+cu130` via index-url) | ✓ SATISFIED | `requirements-cuda.txt` with one cu130 index line, torch +cu130 with 24 index-matching hashes, parity for all other packages |
| SUP-03 | 08-03, 08-04 | Install via `pip install --require-hashes` documented and works | ✓ SATISFIED | Documented in README + SETUP_GUIDE; hash mechanism reproduced (accept/reject); CPU clean-venv install attested exit 0; CUDA install operator-attested |
| SUP-04 | 08-03 | Invariant test updated to the new contract and passes | ✓ SATISFIED | 20-test module; suite `Ran 106 tests … OK`; two mutation controls prove non-vacuity |
| SUP-05 | 08-01, 08-03 | Local `pip-audit` guide (no CI); dev tooling in a separate `requirements-dev` lock | ✓ SATISFIED | Guide in README + SETUP_GUIDE marked "no CI"; no CI config in repo; `requirements-dev.txt` 40 pkgs hashed incl. pip-tools/pip-audit/pyinstaller==6.19.0 |

**Orphaned requirements:** none. The traceability table in `REQUIREMENTS.md` maps exactly SUP-01…SUP-05 to Phase 8, and all five appear in plan `requirements:` frontmatter (08-01: SUP-01/05; 08-02: SUP-02; 08-03: SUP-03/04/05; 08-04: SUP-03). No requirement mapped to Phase 8 is unclaimed.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
| ---- | ---- | ------- | -------- | ------ |
| — | — | No TODO/FIXME/placeholder/empty-return stubs in any phase file | ℹ️ Info | Clean |
| `README.md` / `SETUP_GUIDE.txt` | various | Mentions of `app_config.json` | ℹ️ Info | Pre-existing documentation references only; the test module never reads the config (verified) and no secret is printed |

### Human Verification Required

#### 1. CUDA lock install on CUDA-capable hardware

**Test:** In a scratch venv, run
`py -3 -m venv <tmp>` → `<tmp>\Scripts\python.exe -m pip install --require-hashes -r requirements-cuda.txt` → `<tmp>\Scripts\python.exe -c "import torch;print(torch.__version__, torch.cuda.is_available())"` → delete the venv.
**Expected:** exit 0 with no `DO NOT MATCH THE HASHES`; `torch.__version__` exactly `2.14.0+cu130`; `torch.cuda.is_available()` → `True` on a machine with a usable NVIDIA GPU (`False` is acceptable for *install* verification on a non-GPU machine).
**Why human:** A ~2.8 GB CUDA wheel download cannot be run automatically. The 08-04 Task 3 blocking checkpoint was resolved with the operator typing **`approved`**, but the resume signal carried **no** `torch.cuda.is_available()` value — so this is an operator attestation, not a machine-captured result. Recording the concrete value would close the last non-machine-verified claim.

### Gaps Summary

No gaps. Every roadmap success criterion and every plan `must_haves` artifact/key-link has real, independently inspected evidence in the codebase:

- All three locks are genuine pip-compile outputs (accurate `CUSTOM_COMPILE_COMMAND` headers, no spurious `--no-index`), and every requirement line in every lock is pinned with `==` and immediately followed by at least one `--hash=sha256:` line.
- The CUDA lock differs from the CPU lock in exactly one place (the `torch` pin and its hashes), and those hashes match the live PyTorch cu130 index.
- The rewritten invariant test parses the real lock syntax, passes as part of a 106-test green suite, and is proven non-vacuous in two independent directions.
- The documented `--require-hashes` workflow is real (hash acceptance/rejection reproduced) and there is no CI configuration anywhere in the repository.
- Phase 8 changed no application source (`echo/`, `main.py` show no diff; working tree clean).

The only outstanding item is the human-attested CUDA install (above), which is why the status is `human_needed` rather than `passed`. It is an attestation gap, not a defect.

---

_Verified: 2026-09-23T23:08:11Z_
_Verifier: the agent (gsd-verifier)_
