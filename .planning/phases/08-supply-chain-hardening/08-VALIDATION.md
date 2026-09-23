---
phase: 8
slug: supply-chain-hardening
status: draft
nyquist_compliant: true
wave_0_complete: false
created: 2026-09-23
---

# Phase 8 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | stdlib `unittest` (Python 3.14.3) — deliberately no new dependency |
| **Config file** | none — plain `tests/test_<subject>.py` modules; no `conftest.py`, no `tests/__init__.py` |
| **Quick run command** | `py -3 -m unittest discover -s tests -p "test_requirements_pinning.py" -v` |
| **Full suite command** | `py -3 -m unittest discover -s tests -v` |
| **Estimated runtime** | quick ~1 s · full ~10 s (the `echo.ui.app` test imports `whisper`) |

**Why `unittest` and not `pytest`:** this phase's whole point is "pin every dependency with hashes".
Adding `pytest` would mean either pinning a test framework the app does not ship, or leaving an
unhashed dev tool in the runtime path. Phase 7 already established `unittest` for the same reason;
Phase 8 keeps it. (The dev-tooling lock does add `pip-tools` and `pip-audit` — both dev-only, both
in `requirements-dev.txt`, neither imported by the suite.)

**Why no `tests/__init__.py`:** `py -3 -m unittest discover -s tests` puts the repository root on
`sys.path` (so `import echo.config` resolves) and treats `tests/` as the start directory. Omitting the
package marker keeps `tests/` free of a shared file that parallel same-wave plans would otherwise both
have to create.

**ASCII-only rule for `<automated>`:** PowerShell mangles non-ASCII literals on the command line
(observed repeatedly in this workspace). Every `<automated>` command in this phase is pure ASCII. All
Russian user-facing assertions live **inside** UTF-8 Python test modules, never on the command line.

**Read-only rule:** this phase writes no application state. `app_config.json` (the operator's real API
key, gitignored) must not be read, written, or printed by any Phase 8 test or probe. The lock files
contain no secrets — they are public digests only.

**Disk rule:** any lock-generation command must have `TMP`/`TEMP`/`TMPDIR` pointed at a drive with
≥10 GB free. The default temp dir (`C:`, 1.6 GB free at research time) cannot absorb a pip-tools
download and will fail with `OSError(28) 'No space left on device'`.

---

## Sampling Rate

- **After every task commit:** run that task's `<automated>` command (quick tier)
- **After every plan wave:** full suite plus `py -3 -m pip_audit -r requirements.txt --progress-spinner off`
- **Before `/gsd-verify-work`:** full suite must be green (≥93 tests, including the rewritten pinning
  module) and Plan 08-04 must have passed
- **Max feedback latency:** 30 seconds (lock generation itself is a one-time ~1–2 min step, not a
  sampling step)

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 08-01-01 | 01 | 1 | SUP-01 | T-08-01 | Lock inputs exist and preserve the exact direct pins | probe | `py -3 -c "import pathlib;t=pathlib.Path('requirements.in').read_text();assert t.count('==')==4"` | ❌ W0 | ⬜ pending |
| 08-01-02 | 01 | 1 | SUP-01, SUP-05 | T-08-01 | CPU + dev locks pin every transitive dep with sha256 hashes | probe | `py -3 -c "import pathlib,re;t=pathlib.Path('requirements.txt').read_text();assert re.search(r'^torch==2\.14\.0 \\',t,re.M);assert t.count('--hash=sha256:')==634"` | ❌ W0 | ⬜ pending |
| 08-01-03 | 01 | 1 | SUP-01, SUP-03 | T-08-01, T-08-02 | Hashes are enforced: a tampered hash is rejected | probe | `py -3 -c "import pathlib,re;t=pathlib.Path('requirements.txt').read_text();assert '--no-index' not in t"` | ❌ W0 | ⬜ pending |
| 08-02-01 | 02 | 1 | SUP-02 | T-08-03 | CUDA lock pins `torch==2.14.0+cu130` with index-published hashes | probe | `py -3 -c "import pathlib;t=pathlib.Path('requirements-cuda.txt').read_text();assert 'torch==2.14.0+cu130' in t"` | ❌ W0 | ⬜ pending |
| 08-02-02 | 02 | 1 | SUP-02 | T-08-03 | CUDA lock carries the cu130 index and no CPU torch pin | probe | `py -3 -c "import pathlib;t=pathlib.Path('requirements-cuda.txt').read_text();assert t.count('--extra-index-url https://download.pytorch.org/whl/cu130')==1"` | ❌ W0 | ⬜ pending |
| 08-03-01 | 03 | 2 | SUP-04 | — | Invariant test parses pip-compile lock syntax and is non-vacuous | unit | `py -3 -m unittest discover -s tests -p "test_requirements_pinning.py" -v` | ❌ W0 | ⬜ pending |
| 08-03-02 | 03 | 2 | SUP-03, SUP-05 | T-08-04 | Docs document hash-checked install, CUDA lock, dev lock and pip-audit | probe | `py -3 -c "import pathlib;r=pathlib.Path('README.md').read_text('utf-8');assert '--require-hashes' in r;assert 'pip-audit' in r"` | ❌ W0 | ⬜ pending |
| 08-03-03 | 03 | 2 | SUP-03, SUP-04, SUP-05 | — | Whole suite green with the rewritten pinning module | unit | `py -3 -m unittest discover -s tests -v` | ❌ W0 | ⬜ pending |
| 08-04-01 | 04 | 3 | SUP-03 | T-08-02, T-08-05 | CPU lock installs in hash-checking mode in a clean venv | integration | `py -3 -m venv <tmp> && <tmp>\Scripts\python.exe -m pip install --require-hashes -r requirements.txt` | ❌ W0 | ⬜ pending |
| 08-04-02 | 04 | 3 | SUP-02, SUP-03 | T-08-03 | CUDA lock installs on a CUDA-capable machine | manual | operator-run (see Manual-Only Verifications) | ❌ W0 | ⬜ pending |
| 08-04-03 | 04 | 3 | SUP-05 | T-08-06 | pip-audit reports no known vulnerabilities against the lock | integration | `py -3 -m pip_audit -r requirements.txt --progress-spinner off` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

The durable invariant test **already exists** (`tests/test_requirements_pinning.py`, 62 lines) but
encodes the **old** contract: a flat 4-line `requirements.txt` with no hashes. It therefore cannot
gate the lock-generation tasks — it would fail for the wrong reason.

Resolution (no new scaffold needed):

- [x] `tests/test_requirements_pinning.py` exists — rewritten to the new contract in Plan 08-03
- [x] `tests/` framework — stdlib `unittest`, already installed (no framework install required)
- [ ] Plans 08-01 / 08-02 are gated by deterministic **structural probes** (inline `py -3 -c`
      assertions on hash counts, package sets, and header contents) plus the cheap
      `pip install --require-hashes --dry-run --no-deps` mechanism check. These are transient
      (not committed) — consistent with the Phase 6 D-05 convention of keeping throwaway
      comparators out of the repo.

*Plan 08-03 is the single owner of `tests/test_requirements_pinning.py`, so the three same-wave/earlier
lock plans never touch it.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Hash-checked install of `requirements-cuda.txt` | SUP-02, SUP-03 | ~2.8 GB download of the CUDA torch wheel; must not run as an automated step on the operator's connection | 1. `py -3 -m venv .venv-cuda-check`<br>2. `.venv-cuda-check\Scripts\python.exe -m pip install --require-hashes -r requirements-cuda.txt`<br>3. `.venv-cuda-check\Scripts\python.exe -c "import torch;print(torch.__version__, torch.cuda.is_available())"`<br>4. Expect `2.14.0+cu130` and `True` on a CUDA machine<br>5. Delete the scratch venv |

*Every other phase behavior has automated verification.*

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30 s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
