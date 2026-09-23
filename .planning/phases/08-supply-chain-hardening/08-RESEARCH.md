# Phase 8 — Supply-chain Hardening: Research

**Researched:** 2026-09-23
**Domain:** Python dependency locking (`pip-tools`), hash-checked installs, multi-index (PyTorch CUDA) resolution
**Confidence:** HIGH — every claim below was verified locally in this workspace, not recalled

---

## Summary

Phase 8 turns `requirements.txt` from a 4-line hand-written pin list into a **pip-tools compiled
lock with hashes for every transitive dependency**, adds a **second lock for the CUDA torch build**,
a **dev-tooling lock**, updates the **invariant test**, and documents the **hash-checked install** and
a **local `pip-audit` guide**. No application source code changes.

The phase is small in surface area (6 new/changed data files + 3 docs/tests) but has one genuine
technical trap that would otherwise burn an executor: **`pip-tools --generate-hashes` cannot hash a
`+cu130` local version without downloading every CUDA wheel** (~24 wheels, tens of GB). The research
below pins down the root cause and a verified, fully-reproducible workaround.

### Primary recommendation

| Requirement | Approach |
|-------------|----------|
| SUP-01 | `pip-compile --generate-hashes --allow-unsafe --strip-extras --no-emit-index-url --no-emit-trusted-host` on `requirements.in` → `requirements.txt`. Hashes come from the **PyPI JSON API**, so no wheels are downloaded. |
| SUP-02 | `pip-compile --generate-hashes **--reuse-hashes**` on `requirements-cuda.in`, **seeded** from the CPU lock with the `torch` block swapped for `torch==2.14.0+cu130` + the 24 index-published cu130 hashes. Zero wheel downloads. |
| SUP-03 | `pip install --require-hashes -r <lockfile>`; verified that `--extra-index-url` and `--require-hashes` coexist and that a wrong hash is rejected. |
| SUP-04 | Rewrite `tests/test_requirements_pinning.py` to parse pip-compile lock syntax (backslash continuations + `--hash=` blocks) and assert the new contract across all three locks. |
| SUP-05 | `requirements-dev.in` = `pip-tools` + `pip-audit` → `requirements-dev.txt` with hashes; `pip-audit -r requirements.txt` verified working against a hashed lock. |

---

## Environment (verified in this workspace)

| Fact | Value | How verified |
|------|-------|--------------|
| Python | **3.14.3** (`cp314`), `win_amd64` | `py -3 --version` |
| pip | 26.1.1 (system), 26.2.1 inside the probe venv | `py -3 -m pip --version` |
| pip-tools | **7.6.1** (latest); `requires_python: >=3.9`, `requires_dist: pip>=22.2` (no upper bound) | PyPI JSON + installed & run |
| pip-audit | **2.10.1** (latest) | PyPI JSON + installed & run |
| `pip lock` | exists in pip 26 but is **EXPERIMENTAL** (`pylock.toml`) | `py -3 -m pip lock --help` |
| Installed torch | `2.14.0+cu130` | `pip freeze` |
| Installed direct deps | `openai-whisper==20250625`, `numpy==2.4.4`, `tqdm==4.70.0` | `pip freeze` |
| pip-tools / pip-audit installed? | **No** — neither is present; Phase 8 must install them | `py -3 -m piptools --version` → "No module named piptools" |
| cu130 index reachable | `https://download.pytorch.org/whl/cu130` → HTTP 200 | `Invoke-WebRequest` |
| Free disk | `A:` 49.8 GB, **`C:` 1.6 GB** | `Get-PSDrive` |

**Decision — pip-tools, not `pip lock`.** `pip lock` is experimental and emits `pylock.toml`, a
different contract from what SUP-01/SUP-02/SUP-03/SUP-04 specify (`--generate-hashes`, `pip install
--require-hashes -r <lockfile>`). pip-tools is the requirement's named tool and is verified working
on Python 3.14.3 / pip 26.2.1.

**Decision — dev tools install globally, not into a new venv.** `pyinstaller==6.19.0` is already
installed in the system interpreter (`A:\python`), so "dev-only tooling lives in the system
interpreter" is this repo's established pattern (Level 0 discovery). Phase 8 follows it.

---

## SUP-01 — CPU/default lock (VERIFIED WORKING)

### Command

```powershell
$env:CUSTOM_COMPILE_COMMAND = "pip-compile --generate-hashes --allow-unsafe --strip-extras --no-emit-index-url --no-emit-trusted-host --output-file requirements.txt requirements.in"
py -3 -m piptools compile --generate-hashes --allow-unsafe --strip-extras --no-emit-index-url --no-emit-trusted-host --output-file requirements.txt requirements.in
```

### Verified output

- **24 packages**, **634 `--hash=sha256:` lines**, 697 total lines
- Package set (exact): `certifi, charset-normalizer, colorama, filelock, fsspec, idna, jinja2,
  llvmlite, markupsafe, more-itertools, mpmath, networkx, numba, numpy, openai-whisper, regex,
  requests, sympy, tiktoken, torch, tqdm, typing-extensions, urllib3, setuptools`
- Direct pins: `openai-whisper==20250625`, `torch==2.14.0`, `numpy==2.4.4`, `tqdm==4.70.0`
- `torch==2.14.0` carries **24 hashes** (all PyPI files for that version, every platform/ABI) —
  the lock is cross-platform, not just `cp314-win_amd64`
- **No wheels were downloaded** — `--generate-hashes` sourced every hash from the **PyPI JSON API**
  (`pytools.repositories.pypi._get_hashes_from_pypi`), which publishes digests for every release file

### Two mandatory flags that are easy to miss

1. **`--allow-unsafe` is MANDATORY here.** `torch` declares `Requires-Dist: setuptools>=77.0.3`.
   Without `--allow-unsafe`, pip-tools *omits* `setuptools` from the output (it is an "unsafe"
   package) and `pip install --require-hashes` then fails with *"Hashes are required for all
   dependencies"*. Verified: the successful lock contains `setuptools==84.0.0` with 2 hashes.
2. **`CUSTOM_COMPILE_COMMAND` is needed for a truthful header.** `pip-tools`' `get_compile_command()`
   records *every* plain flag unconditionally (`piptools/utils.py:379-388`), so the auto-generated
   header always contains a bogus `--no-index` even when it was never used. Setting
   `CUSTOM_COMPILE_COMMAND` (`piptools/writer.py:138`) replaces the header with an accurate,
   reproducible command. **Verified:** with it set, the header reads
   `#    pip-compile --generate-hashes --allow-unsafe --strip-extras --output-file requirements.txt requirements.in`
   and contains no `--no-index`.

### `--strip-extras` / `--no-emit-index-url`

- `--strip-extras` — pip-tools 7.x still emits `pkg[extra]==x` for extras unless stripped; stripping
  keeps one line per distribution (pip-tools 8 makes this the default).
- `--no-emit-index-url` / `--no-emit-trusted-host` — the CPU lock is pure PyPI, so no index line is
  needed; omitting it keeps the lock free of environment-specific URLs.

---

## SUP-02 — CUDA lock (the trap, and the verified fix)

### The trap

`pip-tools` resolves hashes as follows (`piptools/repositories/pypi.py`):

```python
def _get_req_hashes(self, ireq):
    matching_candidates = self._get_matching_candidates(ireq)      # ALL wheels (see below)
    pypi_hashes_by_link = self._get_hashes_from_pypi(ireq)         # PyPI JSON API, keyed by URL
    pypi_hashes  = {pypi_hashes_by_link[c.link.url] for c in matching_candidates
                    if c.link.url in pypi_hashes_by_link}
    local_hashes = {self._get_file_hash(c.link) for c in matching_candidates
                    if c.link.url not in pypi_hashes_by_link}       # DOWNLOADS the wheel
```

Two compounding problems for `torch==2.14.0+cu130`:

1. **`_get_hashes_from_pypi` returns `{}`.** It queries the **PyPI JSON API** for
   `releases[version]`; PyPI has no `2.14.0+cu130` release. Every candidate therefore falls into
   `local_hashes` → `_get_file_hash()` **downloads each wheel** to hash it.
2. **`resolve_hashes()` runs inside `repository.allow_all_wheels()`** (`piptools/resolver.py:168`),
   which monkey-patches `pip.Wheel.supported` to always return `True`. So `_get_matching_candidates`
   returns **all 24** `torch-2.14.0+cu130` wheels (cp310…cp314t × manylinux aarch64/x86_64 ×
   win_amd64) — roughly **tens of GB**.

**Observed failure:** the naive `pip-compile --generate-hashes --extra-index-url
https://download.pytorch.org/whl/cu130` run died with
`pip._vendor.urllib3.exceptions.ProtocolError: Connection broken: OSError(28, 'No space left on device')`
because pip-tools downloads into a temp dir on `C:` (1.6 GB free).

### A third trap: `--extra-index-url` poisons every other package too

The PyTorch index is a **full mirror**, not a torch-only index. Verified HTTP 200 for
`/whl/cu130/{numpy,tqdm,sympy,networkx,filelock,fsspec,jinja2}/` (the `numpy` page alone is 2.2 MB,
listing 213 `numpy-2.4.4-*` wheels). So with `--extra-index-url` active, `_get_matching_candidates`
pulls in **cu130-hosted copies of numpy/tqdm/sympy/…** whose URLs are absent from the PyPI JSON map →
pip-tools tries to download and hash *those* too. This is why adding the extra index made an
otherwise-fine run explode.

**Good news (verified):** the mirror is **byte-identical**. The `cu130` published sha256 for
`numpy-2.4.4-cp314-cp314-win_amd64.whl` is `715d1c092715954784bc79e1174fc2a90093dc4dc84ea15eb14dad8abdcdeb74`
— exactly the PyPI-published digest. So hash-checked installs are unambiguous regardless of which
index serves the file.

### The fix — seed the lock and reuse hashes (VERIFIED, returncode 0, zero downloads)

`pip-tools`' `--reuse-hashes` (default **on**) routes hash lookup through
`LocalRequirementsRepository.get_hashes` (`piptools/repositories/local.py:89-100`), which returns the
**existing output file's** hashes when that file already pins the same version:

```python
existing_pin = self._reuse_hashes and self.existing_pins.get(key_from_ireq(ireq))
if existing_pin and ireq_satisfied_by_existing_pin(ireq, existing_pin):
    hexdigests = existing_pin.hash_options.get(FAVORITE_HASH)
    if hexdigests:
        return {":".join([FAVORITE_HASH, d]) for d in hexdigests}   # no download
return self.repository.get_hashes(ireq)
```

`existing_pins` is parsed from `--output-file` (`piptools/scripts/compile.py:336-364`). So if the
output file is **pre-seeded with the complete desired lock**, `--generate-hashes --reuse-hashes`
reuses every hash and downloads nothing.

**Procedure (verified end-to-end):**

1. Build the seed = a copy of `requirements.txt` with the `torch` block replaced by
   `torch==2.14.0+cu130` + all 24 cu130 hashes, prefixed with
   `--extra-index-url https://download.pytorch.org/whl/cu130`.
2. Write `requirements-cuda.in` (the four direct deps + the `--extra-index-url` line).
3. Run:
   ```powershell
   $env:CUSTOM_COMPILE_COMMAND = "pip-compile --generate-hashes --reuse-hashes --allow-unsafe --strip-extras --output-file requirements-cuda.txt requirements-cuda.in"
   py -3 -m piptools compile --generate-hashes --reuse-hashes --allow-unsafe --strip-extras --output-file requirements-cuda.txt requirements-cuda.in
   ```

**Verified result:**

- returncode **0**, **zero wheel downloads**
- **24 packages** — the *same set* as the CPU lock
- **634 `--hash=sha256:` lines** — the same count as the CPU lock (only torch's hash *values* differ)
- `torch==2.14.0+cu130` present; `--extra-index-url https://download.pytorch.org/whl/cu130` emitted
  exactly once; header clean (no `--no-index`)

### Where the 24 cu130 hashes come from (no download needed)

The index publishes the digest in the href fragment:

```
https://download-r2.pytorch.org/whl/cu130/torch-2.14.0%2Bcu130-cp314-cp314-win_amd64.whl#sha256=78ab64d1…
```

Note the version is **URL-encoded as `2.14.0%2Bcu130`** — a regex written against `2.14.0+cu130`
matches **0** entries. Extraction command (verified → exactly 24):

```powershell
py -3 -c "import re,urllib.request; h=urllib.request.urlopen('https://download.pytorch.org/whl/cu130/torch/',timeout=90).read().decode('utf-8','replace'); print(sorted(set(re.findall(r'torch-2\.14\.0%2Bcu130-[^\"#]+\.whl#sha256=([0-9a-f]{64})', h))))"
```

Known-good values to cross-check against:

| Wheel | sha256 |
|-------|--------|
| `torch-2.14.0+cu130-cp314-cp314-win_amd64.whl` | `78ab64d12e478c8baedc4d90e662f6ffca2b6cb8a872a02b734a8aa3e00277eb` |
| count of `torch-2.14.0+cu130-*.whl` entries | **24** |

### `torch 2.14.0+cu130` dependency closure (from PEP 658 metadata)

`filelock`, `typing-extensions>=4.10.0`, `setuptools>=77.0.3`, `sympy>=1.13.3`,
`networkx>=2.5.1`, `jinja2`, `fsspec>=0.8.5` — **no `nvidia-*` packages on Windows** (CUDA is
bundled in the wheel). `Requires-Python: >=3.10`. This closure is identical to the CPU `torch`
build's, which is why the two locks share a package set.

---

## SUP-03 — Hash-checked install (VERIFIED)

| Claim | Result |
|-------|--------|
| `--require-hashes` coexists with `--extra-index-url` | **Yes.** `pip install --require-hashes --dry-run --no-deps -r <file with --extra-index-url …/cu130 + tqdm>` → `Looking in indexes: https://pypi.org/simple, https://download.pytorch.org/whl/cu130` … `Would install tqdm-4.70.0`, exit 0 |
| A wrong hash is rejected | **Yes.** Substituting `sha256:0000…` → `ERROR: THESE PACKAGES DO NOT MATCH THE HASHES FROM THE REQUIREMENTS FILE.` |
| PyPI-only hashes are sufficient even when the file also lists the cu130 index | **Yes.** numpy's 72 PyPI hashes + `--extra-index-url …/cu130` → `Would install numpy-2.4.4`, exit 0 (the mirror is byte-identical) |
| `openai-whisper==20250625` has a wheel? | **No — sdist only** (`openai_whisper-20250625.tar.gz`). The lock's single hash is the sdist hash. |

### Caveats that must be documented

1. **`openai-whisper` has no wheel**, so `pip install --require-hashes` **builds it from sdist**.
   PEP 517 **build-time** dependencies (`setuptools`, `wheel`) are **not** covered by
   `--require-hashes` — a residual supply-chain gap. `--only-binary :all:` is therefore **not** an
   option. Document as an accepted residual risk.
2. **The CPU lock installs CPU `torch`.** `torch==2.14.0` (no local tag) selects the PyPI CPU wheel.
   A CUDA user must use `requirements-cuda.txt`.
3. **PEP 440 nuance:** `SpecifierSet("==2.14.0").contains("2.14.0+cu130")` is **`True`** (local
   segment ignored), while `==2.14.0+cu130` does *not* match `2.14.0`. Consequence: on a machine
   where `torch==2.14.0+cu130` is already installed, `pip install --require-hashes -r requirements.txt`
   considers the requirement satisfied and **will not downgrade it**. Behaviour differs between a
   fresh venv and this machine — worth a one-line note in the docs.
4. **CUDA install is a ~2.8 GB download.** Do not run it as an automated step; it is a
   `checkpoint:human-verify`.
5. The transitive pins in the new lock **float above what is currently installed** (e.g.
   `typing-extensions` 4.15.0 → 4.16.0, `urllib3` 2.7.0 → 2.8.0, `setuptools` 82.0.1 → 84.0.0,
   `filelock` 3.32.3 → 4.0.1, `fsspec` 2026.7.0 → 2026.9.0, `networkx` 3.6.1 → 3.7,
   `regex` 2026.9.3 → 2026.9.10, `idna` 3.19 → 3.20). The **direct** deps match the installed
   versions exactly. Any "pins match installed versions" assertion must therefore be scoped to the
   four direct deps.

---

## SUP-04 — Invariant test contract delta

`tests/test_requirements_pinning.py` (62 lines, `unittest`) currently assumes a **flat 4-line
`requirements.txt`** and will break on a pip-compile lock:

| Existing test | Why it breaks | New contract |
|---------------|---------------|--------------|
| `test_every_entry_is_an_exact_pin` | `setUp` keeps `--hash=…` continuation lines (they don't start with `#`); `assertIn("==", line)` fails on them | Parse pip-compile blocks: a requirement starts at `^name==…`, its hashes are the following `--hash=` lines, backslash continuations are not standalone requirements |
| `test_pin_set_is_exactly_expected` | `dict(line.split("=="))` explodes on 3-element hashed lines | Compare the **direct** pins (`openai-whisper`, `torch`, `numpy`, `tqdm`) against the expected table |
| `test_srt_is_no_longer_declared` | still valid — no package named `srt` is in any lock | Keep, extended to all three locks |
| `test_pins_match_the_installed_versions` | transitive pins now differ from the installed env | Scope to the four **direct** deps only |
| README/SETUP_GUIDE assertions | still valid | Preserve exactly: README contains `echo/srt.py`; README does **not** contain `declared, but unused` or `| srt `; SETUP_GUIDE does **not** contain `4.4 srt` |

**New assertions to add:** every lock requirement pinned `==` with ≥1 `sha256` hash; all three
lockfiles exist; `requirements.in` / `requirements-cuda.in` / `requirements-dev.in` exist as the
source-of-truth inputs; `requirements-cuda.txt` pins `torch==2.14.0+cu130` and contains
`--extra-index-url https://download.pytorch.org/whl/cu130`; `requirements-dev.txt` contains
`pip-tools` and `pip-audit`; compile headers contain no `--no-index`; README/SETUP_GUIDE contain
`--require-hashes` and a `pip-audit` mention.

**Anti-vacuity requirement:** the suite currently has 93 tests (per `07-04-SUMMARY.md`). The rewritten
module must be proven non-vacuous with a **negative control** — corrupt one hash in a temp copy and
show the parser rejects it. (This mirrors the truth-table / negative-control discipline used in
Phase 7.)

---

## SUP-05 — Dev lock + local `pip-audit` guide (VERIFIED)

```powershell
$env:CUSTOM_COMPILE_COMMAND = "pip-compile --generate-hashes --allow-unsafe --strip-extras --no-emit-index-url --no-emit-trusted-host --output-file requirements-dev.txt requirements-dev.in"
py -3 -m piptools compile --generate-hashes --allow-unsafe --strip-extras --no-emit-index-url --no-emit-trusted-host --output-file requirements-dev.txt requirements-dev.in
```

`requirements-dev.in` = `pip-tools==7.6.1`, `pip-audit==2.10.1`, `pyinstaller==6.19.0` (SUP-05 plus the
user decision to pin the packaging tool now; `pyinstaller-hooks-contrib` is pinned transitively by
pip-compile and is NOT listed in the `.in` file).

**`pip-audit` against a hashed lock — VERIFIED:**

```powershell
py -3 -m pip_audit -r requirements.txt --progress-spinner off
# → No known vulnerabilities found
```

pip-audit parses the `--hash=` continuation lines without complaint. Module name is `pip_audit`,
console script is `pip-audit`. **No CI** — a local, operator-run command only.

---

## Documentation surfaces

| File | Encoding | Line endings | Relevant region |
|------|----------|--------------|-----------------|
| `README.md` | UTF-8 | **CRLF** (445 CRLF, 0 bare LF) | `## Tech Stack` (~L199 claims "pinned with `==`"), `### 3. Install dependencies` (~L236-240 `pip install -r requirements.txt`) |
| `SETUP_GUIDE.txt` | UTF-8 | **CRLF** (626 CRLF, 0 bare LF) | `4. ШАГ 2: PIP-ПАКЕТЫ` (~L217-292). Russian text. Do **not** touch `11. ПРИЛОЖЕНИЕ: пакет echo/` |

Both are UTF-8 (the garbled console output earlier was only the CP866 console codepage, not the file
encoding). **Preserve CRLF and UTF-8 on every edit.** `<automated>` command lines must stay pure
ASCII — PowerShell mangles non-ASCII literals on the command line (established Phase 7 rule).

---

## Validation Architecture

### Test infrastructure

| Property | Value |
|----------|-------|
| Framework | stdlib `unittest` (Python 3.14.3) — deliberately no new dependency |
| Config file | none — plain `tests/test_<subject>.py` modules, no `conftest.py`, no `tests/__init__.py` |
| Quick run command | `py -3 -m unittest discover -s tests -p "test_requirements_pinning.py" -v` |
| Full suite command | `py -3 -m unittest discover -s tests -v` |
| Estimated runtime | quick ~1 s · full ~10 s |

### Feedback sampling

- **After every task commit:** that task's `<automated>` command (quick tier)
- **After every plan wave:** full suite + `py -3 -m pip_audit -r requirements.txt --progress-spinner off`
- **Before `/gsd-verify-work`:** full suite green (≥93 tests, incl. the rewritten pinning module)
- **Max feedback latency:** 30 s (lock generation itself is a one-time ~1-2 min step, not a sampling step)

### Wave 0 / pre-test tier

The durable invariant test **already exists** (`tests/test_requirements_pinning.py`) but encodes the
old contract, so it cannot gate the lock-generation tasks. Lock generation (Plans 08-01, 08-02) is
verified with **deterministic, ASCII-only structural probes** (inline `py -3 -c` one-liners asserting
hash counts, package sets, and header contents) plus the cheap `pip install --require-hashes
--dry-run --no-deps` mechanism check. The rewritten invariant test lands in Plan 08-03 (single owner
of that file) and becomes the durable gate.

### Manual-only verification

| Behavior | Requirement | Why manual | Instructions |
|----------|-------------|-----------|--------------|
| Real hash-checked install of `requirements-cuda.txt` | SUP-02, SUP-03 | ~2.8 GB download; must not run as an automated step | `py -3 -m venv <tmp>` → `pip install --require-hashes -r requirements-cuda.txt` in a scratch venv; confirm `torch 2.14.0+cu130` imports and `torch.cuda.is_available()` matches the operator's GPU |

Everything else (CPU lock install, pip-audit, invariant tests, structural probes) is automated.

---

## Pitfalls

| # | Pitfall | Avoidance |
|---|---------|-----------|
| 1 | Running `pip-compile --generate-hashes` on the cu130 index without a seed → downloads all 24 CUDA wheels (~tens of GB) and dies with `OSError(28)` | Always seed `requirements-cuda.txt` from `requirements.txt` first and pass `--reuse-hashes` |
| 2 | Omitting `--allow-unsafe` → `setuptools` dropped from the lock → `--require-hashes` install fails | Always pass `--allow-unsafe` |
| 3 | Auto-generated header contains a spurious `--no-index` | Always set `CUSTOM_COMPILE_COMMAND` |
| 4 | Regex for cu130 hashes written as `2.14.0+cu130` matches 0 entries | Match the URL-encoded `2.14.0%2Bcu130` |
| 5 | Letting the default temp dir (on `C:`, 1.6 GB free) absorb pip-tools downloads | Point `TMP`/`TEMP`/`TMPDIR` at a drive with ≥10 GB free for any lock run; with the seed in place nothing large should download anyway |
| 6 | `--extra-index-url` also pulls mirrored numpy/tqdm/sympy into hashing | Covered by the seed; do **not** try to "fix" it by dropping the extra index — torch needs it |
| 7 | Editing `README.md` / `SETUP_GUIDE.txt` and losing CRLF or UTF-8 | Read before edit; verify CRLF count is unchanged after the edit |
| 8 | Asserting that all lock pins match installed versions | Only the four direct deps match; transitive pins float |
| 9 | Assuming `openai-whisper` has a wheel | It is sdist-only; `--only-binary :all:` will fail |
| 10 | Removing `requirements.txt`'s 4 direct pins before the lock exists | Generate the lock first; the `.in` files preserve the exact same direct pins |

---

## Files touched by Phase 8

**New:** `requirements.in`, `requirements-cuda.in`, `requirements-cuda.txt`,
`requirements-dev.in`, `requirements-dev.txt`
**Rewritten:** `requirements.txt` (4 lines → compiled lock)
**Edited:** `tests/test_requirements_pinning.py`, `README.md`, `SETUP_GUIDE.txt`
**Unchanged:** all application source (`echo/**`, `main.py`), `.gitignore` (locks are not ignored),
`app_config.json` (gitignored)

---

## Sources

- pip docs — Secure installs / hash-checking mode: https://pip.pypa.io/en/stable/topics/secure-installs/
- pip docs — `pip lock` (experimental): https://pip.pypa.io/en/stable/cli/pip_lock/
- pip-tools source, installed 7.6.1 — `repositories/pypi.py` (`_get_req_hashes`, `_get_hashes_from_pypi`,
  `_get_file_hash`, `allow_all_wheels`), `repositories/local.py` (`get_hashes`), `resolver.py:160-169`,
  `scripts/compile.py:336-364`, `utils.py:305-401`, `writer.py:129-150`
- PyPI JSON API: `https://pypi.org/pypi/{project}/{version}/json` (hash source for SUP-01)
- PyTorch cu130 wheel index: `https://download.pytorch.org/whl/cu130/torch/`
- PEP 658 metadata: `https://download.pytorch.org/whl/cu130/torch-2.14.0%2Bcu130-cp314-cp314-win_amd64.whl.metadata`
- PEP 440 (local version segments and `==` matching)
- `.planning/phases/07-security-hardening/07-VALIDATION.md` (test infrastructure conventions)
- `.planning/phases/07-security-hardening/07-VERIFICATION.md`, `.planning/STATE.md` (SEC-06 baseline)
