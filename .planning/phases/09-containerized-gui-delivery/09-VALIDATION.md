---
phase: 9
slug: containerized-gui-delivery
status: draft
nyquist_compliant: true
wave_0_complete: false
created: 2026-10-01
---

# Phase 9 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | stdlib `unittest` (Python 3.14.3) — deliberately no new dependency |
| **Config file** | none — plain `tests/test_<subject>.py` modules; no `conftest.py`, no `tests/__init__.py` |
| **Quick run command** | `py -3 -m unittest discover -s tests -p "test_docker_delivery.py" -v` |
| **Full suite command** | `py -3 -m unittest discover -s tests -v` |
| **Estimated runtime** | quick ~1 s · full ~10–15 s (the `echo.ui.app` test imports `whisper`) |

**Why `unittest` and not `pytest`:** this repo has deliberately avoided a test framework dependency
since Phase 7 (a memory-bound m4rgoo could afford it; the locking phase could not). Phase 8 extended
that rule to every new module. The Docker-delivery tests are static file assertions, so `unittest` is
more than sufficient.

**Why no `tests/__init__.py`:** `py -3 -m unittest discover -s tests` puts the repository root on
`sys.path` (so `import echo.config` resolves) and treats `tests/` as the start directory. Omitting the
package marker keeps `tests/` free of a shared file that parallel same-wave plans would otherwise both
have to create.

**ASCII-only rule for `<automated>`:** PowerShell mangles non-ASCII literals on the command line
(observed repeatedly in this workspace). Every `<automated>` command in this phase is pure ASCII. All
Russian user-facing assertions live **inside** UTF-8 Python test modules, never on the command line.

**Read-only rule:** no Phase 9 test reads, writes, or prints `app_config.json` (the operator's real API
key, gitignored). Static tests read committed sources (`Dockerfile`, `docker/entrypoint.sh`,
`README.md`, `BUILD.md`) and line-scan them for required literals.

**Docker rule:** automated Docker steps use only the **CPU** image (`echo:cpu`) built from the repo's
own `Dockerfile`. No CUDA image is built (that would need the `+cu130` download). Container runs are
`--rm`, named for easy cleanup, and bound to `127.0.0.1` so no port is opened on the LAN.

**Disk rule:** `docker save` output is multi-GB. Any save/load step must target `A:` (101 GB free at
research time). `C:` had only 6.6 GB free.

---

## Sampling Rate

- **After every task commit:** run that task's `<automated>` command (quick tier)
- **After every plan wave:** full suite plus `docker build -t echo:cpu .` once wave 1 has landed
- **Before `/gsd-verify-work`:** full suite green (≥106 tests + the new modules) and Plan 09-04 passed
- **Max feedback latency:** 30 seconds for the quick tier (the image build is a one-time multi-minute
  step, not a sampling step)

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 09-01-01 | 01 | 1 | CNTR-01, CNTR-02 | T-09-01 | Image installs `x11vnc`/`novnc`/`websockify`, exposes `6080`, and never bakes `app_config.json` | static | `py -3 -c "import pathlib;d=pathlib.Path('Dockerfile').read_text();assert 'x11vnc' in d and 'novnc' in d and 'websockify' in d;assert 'EXPOSE 6080' in d;assert 'COPY app_config.json' not in d"` | ❌ W0 | ⬜ pending |
| 09-01-02 | 01 | 1 | CNTR-01, CNTR-02 | T-09-02 | Entrypoint starts Xvfb/app/x11vnc/websockify, binds VNC to loopback, has a signal trap | static | `py -3 -c "import pathlib;e=pathlib.Path('docker/entrypoint.sh').read_text();assert 'Xvfb' in e and 'python -m echo' in e and 'x11vnc' in e and 'websockify' in e;assert '-localhost' in e and 'trap' in e and '--web /usr/share/novnc/' in e"` | ❌ W0 | ⬜ pending |
| 09-01-03 | 01 | 1 | CNTR-01, CNTR-02 | T-09-01, T-09-02 | Durable invariant test for the delivered image artifacts | unit | `py -3 -m unittest discover -s tests -p "test_docker_delivery.py" -v` | ❌ W0 | ⬜ pending |
| 09-02-01 | 02 | 1 | CNTR-03 | T-09-03 | `ECHO_CONFIG_PATH` override; default path and `validate_base_url` unchanged | static | `py -3 -c "import pathlib;c=pathlib.Path('echo/config.py').read_text();assert 'ECHO_CONFIG_PATH' in c and 'resolve_config_path' in c;assert 'def validate_base_url' not in c"` | ❌ W0 | ⬜ pending |
| 09-02-02 | 02 | 1 | CNTR-03 | T-09-03 | Override resolves only when set; default is the repo-root file | unit | `py -3 -m unittest discover -s tests -p "test_config_env_override.py" -v` | ❌ W0 | ⬜ pending |
| 09-03-01 | 03 | 2 | CNTR-04 | T-09-04 | Docs give VNC run flags, mounts, and `docker save`/`load` deployment | static | `py -3 -c "import pathlib;b=pathlib.Path('BUILD.md').read_text('utf-8');assert 'vnc.html' in b and '6080' in b and 'docker save' in b and 'ECHO_CONFIG_PATH' in b"` | ❌ W0 | ⬜ pending |
| 09-03-02 | 03 | 2 | CNTR-03, CNTR-04 | T-09-04 | README + SETUP_GUIDE expose the container path and the mounted-config contract; UTF-8/CRLF preserved | static | `py -3 -c "import pathlib;r=pathlib.Path('README.md').read_text('utf-8');s=pathlib.Path('SETUP_GUIDE.txt').read_text('utf-8');assert '6080' in r and 'Docker' in r;assert '6080' in s or 'Docker' in s"` | ❌ W0 | ⬜ pending |
| 09-03-03 | 03 | 2 | CNTR-03, CNTR-04 | T-09-04 | Durable doc invariants: VNC URL, save/load, config-mount contract, UTF-8/CRLF | unit | `py -3 -m unittest discover -s tests -p "test_docker_docs.py" -v` | ❌ W0 | ⬜ pending |
| 09-03-04 | 03 | 2 | CNTR-01, CNTR-02, CNTR-03, CNTR-04 | — | Whole suite green after the doc/test additions | unit | `py -3 -m unittest discover -s tests -v` | ❌ W0 | ⬜ pending |
| 09-04-01 | 04 | 3 | CNTR-01, CNTR-02 | T-09-05 | Image builds and the container serves `/vnc.html` 200 + WS 101 | integration | `docker build -t echo:cpu . && docker run -d --rm -p 127.0.0.1:6080:6080 --name echo-vnc echo:cpu` then the ASCII HTTP/WS probe | ❌ W0 | ⬜ pending |
| 09-04-02 | 04 | 3 | CNTR-03, CNTR-04 | T-09-06 | Directory-mounted config is writable by the atomic writer; `docker save`/`load` round-trips | integration | `py -3 -m unittest discover -s tests -v` plus the container config round-trip probe and `docker save`/`docker load` | ❌ W0 | ⬜ pending |
| 09-04-03 | 04 | 3 | CNTR-01, CNTR-02 | T-09-05 | Operator sees and uses the GUI in a browser | manual | operator-run (see Manual-Only Verifications) | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

No new framework or scaffold is needed — `tests/` already exists and uses stdlib `unittest`.

- [x] `tests/` framework — exists, no install required
- [ ] `tests/test_docker_delivery.py` — created by Plan 09-01 (owner: Plan 09-01; no other plan
      touches it, so same-wave plans never collide)
- [ ] `tests/test_config_env_override.py` — created by Plan 09-02 (owner: Plan 09-02)
- [ ] `tests/test_docker_docs.py` — created by Plan 09-03 (owner: Plan 09-03)

Plans 09-01 and 09-02 are independent (disjoint files) and can run in the same wave; each one owns the
one new test file it introduces. There is no "expectation written before the artifact" gap: the tests
assert on artifacts the same plan creates.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| The tkinter GUI is **visibly** served in the browser and is usable | CNTR-01, CNTR-02 | Automation can prove HTTP 200 + a `101` WebSocket upgrade, but not that a human sees a working window | 1. `docker build -t echo:cpu .`<br>2. `docker run --rm -p 127.0.0.1:6080:6080 -v "${PWD}\config:/config" -e ECHO_CONFIG_PATH=/config/app_config.json echo:cpu`<br>3. Open `http://localhost:6080/vnc.html`<br>4. Confirm the Echo window renders and the UI is interactive<br>5. `docker stop echo-vnc` |
| Deploy the image on a second PC via `docker save`/`load` | CNTR-04 | Requires a second machine with Docker Desktop | Follow the `BUILD.md` deployment section on the target PC |

Everything else (image build, container startup, HTTP 200, WS 101, config round-trip, `docker
save`/`load` round-trip, full suite) is automated.

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30 s (quick tier)
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
