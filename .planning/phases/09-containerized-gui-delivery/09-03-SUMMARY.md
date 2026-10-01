---
phase: 09-containerized-gui-delivery
plan: 03
subsystem: infra
tags: [docs, docker, vnc, novnc, echo-config-path, docker-save, docker-load, crlf, utf8, unittest, cntr-03, cntr-04]

# Dependency graph
requires:
  - plan: "09-01"
    provides: "the browser-VNC image (EXPOSE 6080, entrypoint defaults: Xvfb :99 1440x900x24, x11vnc -localhost, websockify --web on 6080)"
  - plan: "09-02"
    provides: "ECHO_CONFIG_PATH-aware config path resolver (directory mount /config/app_config.json; default unchanged)"
provides:
  - "BUILD.md — complete build/run/mounts/security/deploy/debugging guide for the browser-VNC image"
  - "README.md — 'Run in Docker (browser GUI)' pointer section"
  - "SETUP_GUIDE.txt — Russian 'СЦЕНАРИЙ D. Docker (GUI в браузере)' step"
  - "tests/test_docker_docs.py — 15 durable documentation invariants (content + UTF-8/CRLF)"
affects: [plan-09-04, phase-09-verify-work, cntr-04]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "docs document the directory config mount + ECHO_CONFIG_PATH and explicitly warn that the single-file mount breaks os.replace (EBUSY)"
    - "docs default to a loopback port binding; LAN exposure is opt-in and paired with VNC_PASSWORD; plain ws:// (no TLS) is stated"
    - "deployment covered both ways: docker save/load (offline tar, multi-GB) and registry tag/push/pull"
    - "durable static tests assert doc invariants (including UTF-8 + CRLF-only) without building anything"

key-files:
  created:
    - tests/test_docker_docs.py
  modified:
    - BUILD.md
    - README.md
    - SETUP_GUIDE.txt

key-decisions:
  - "BUILD.md documents a single-line docker run so the command is identical in PowerShell and bash (no line-continuation anchors)"
  - "The single-file config mount is never offered as an option: BUILD.md explicitly documents the EBUSY failure and mandates a directory mount at /config"
  - "Security defaults to -p 127.0.0.1:6080:6080; -p 6080:6080 is opt-in and must be paired with -e VNC_PASSWORD; noVNC's plain ws:// limitation is stated with reverse-proxy TLS as the remedy"
  - "SETUP_GUIDE.txt gained СЦЕНАРИЙ D inside the existing section 8 (no renumbering), preserving its numbered Russian style"
  - "README.md and SETUP_GUIDE.txt edits are purely additive and both stayed UTF-8 CRLF-only (0 bare LF), per the Phase 8 encoding rule"
  - "Dockerfile/entrypoint assertions stay in tests/test_docker_delivery.py (Plan 09-01); this plan owns only doc invariants"

patterns-established:
  - "Doc pitfalls are enforced by tests: test_docker_docs.py asserts ECHO_CONFIG_PATH=/config/app_config.json, the loopback binding, VNC_PASSWORD and docker save/load remain documented"
  - "Encoding convention is test-guarded: EncodingTests fails the suite if README.md or SETUP_GUIDE.txt gains a bare LF"

requirements-completed: [CNTR-03, CNTR-04]

# Metrics
duration: ~4min
completed: 2026-10-01
---

# Phase 9 Plan 03: Container Delivery Documentation Summary

**BUILD.md rewritten into a runnable build/run/deploy guide for the browser-VNC image (loopback noVNC on 6080, `/config` + `ECHO_CONFIG_PATH` directory mount, corporate https endpoint, Whisper cache volume, `docker save`/`docker load`), with matching README and Russian SETUP_GUIDE pointers and 15 durable doc invariants — full suite 144 tests OK**

## Performance

- **Duration:** ~4 min
- **Started:** 2026-10-01T03:49:33Z
- **Completed:** 2026-10-01T03:53:04Z
- **Tasks:** 3
- **Files modified:** 4 (1 created, 3 modified)

## Accomplishments

- **Task 1 — `BUILD.md` is now a complete operator guide.** Added the build command, a single-line `docker run` (loopback binding, `/config` + `ECHO_CONFIG_PATH=/config/app_config.json`, `echo-whisper` volume, `/root/audio`), the `http://localhost:6080/vnc.html` URL, port/security guidance (`127.0.0.1:6080:6080` default, opt-in `-p 6080:6080` + `VNC_PASSWORD`, plain `ws://`), the corporate **https** config JSON, the explicit single-file-mount `EBUSY` warning, audio/results guidance, the `/root/.cache/whisper` cache, `docker save`/`docker load` + registry deployment, the CPU-only/GPU note, debugging, and the preserved dependency-install and lock-regeneration sections.
- **Task 2 — user docs point at the container path.** `README.md` gained `## Run in Docker (browser GUI)` after `## Run`; `SETUP_GUIDE.txt` gained `СЦЕНАРИЙ D. Docker (GUI в браузере)` in section 8. Both edits are purely additive; existing `srt.py`/lock mentions untouched. Byte checks confirm **UTF-8 with zero bare LF** in both files.
- **Task 3 — invariants locked in.** `tests/test_docker_docs.py` adds **15** stdlib `unittest` cases across `BuildDocTests`, `ReadmeDocTests`, `EncodingTests`, including the config override, save/load, loopback binding, `VNC_PASSWORD`, `pip-compile`, `https`, and no-bare-LF checks.
- **Verification:** quick tier 15/15 OK; full suite **144/144 OK** (baseline 129 after 09-01/09-02 + 15 new).

## Task Commits

Each task was committed atomically:

1. **Task 1: Rewrite BUILD.md as the container build/run/deploy guide** — `0ba7e11` (docs)
2. **Task 2: Point README and SETUP_GUIDE at the Docker workflow** — `577139c` (docs)
3. **Task 3: Add tests/test_docker_docs.py** — `2cd91c3` (test)

**Plan metadata:** _pending final metadata commit_ (docs: complete plan)

## Files Created/Modified

- `BUILD.md` — rewritten top half documents the browser-VNC delivery (build, single-line run, security, corporate https config via a `/config` directory mount, audio, Whisper cache, `docker save`/`load` + registry, GPU note, debugging); bottom half preserves "How dependencies are installed" and "Regenerating the locks".
- `README.md` — new `## Run in Docker (browser GUI)` section (build/run/URL + `BUILD.md` link); +11 lines, existing content untouched.
- `SETUP_GUIDE.txt` — new `СЦЕНАРИЙ D. Docker (GUI в браузере)` in section 8; +21 lines, no renumbering, section 11 untouched.
- `tests/test_docker_docs.py` — 15 stdlib `unittest` cases asserting the doc contract and the UTF-8/CRLF convention.

## Decisions Made

- **Single-line `docker run`** — avoids PowerShell-vs-bash line-continuation inconsistencies; the documented command is copy-paste identical on both.
- **Single-file mount forbidden** — BUILD.md names the `os.replace` → `EBUSY` failure and mandates the directory mount, so an operator cannot be led into the broken "Save Settings" path.
- **Secure-by-default binding** — docs default to `127.0.0.1:6080:6080`; LAN exposure is opt-in *and* paired with `VNC_PASSWORD`; the absence of TLS (`ws://`) is stated with reverse-proxy TLS as the remedy.
- **Surgical doc edits** — README/SETUP_GUIDE changes are purely additive and preserve the required UTF-8 + CRLF-only encoding; SETUP_GUIDE keeps its existing numbering by adding a scenario, not a new numbered section.
- **Test ownership split** — doc invariants live here; `Dockerfile`/entrypoint assertions remain in `tests/test_docker_delivery.py` (Plan 09-01).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] CRLF normalization of SETUP_GUIDE.txt after the edit**

- **Found during:** Task 2 (README + SETUP_GUIDE edits)
- **Issue:** After the insertion, `SETUP_GUIDE.txt` contained **1 bare LF** (the file must be CRLF-only). The edit boundary also left two cosmetic whitespace differences (a leading space added to an 80-dash separator line and a doubled indent on the section-9 header).
- **Fix:** Byte-preserving normalization of the file back to CRLF-only (`raw.replace(b"\r\n", b"\n").replace(b"\n", b"\r\n")`) and restoration of the two whitespace artifacts, so the final `git diff` is **purely additive** (README +11, SETUP_GUIDE +21, zero deletions).
- **Files modified:** `SETUP_GUIDE.txt` (same file as the planned edit; no scope change)
- **Verification:** `raw.count(b"\n") == raw.count(b"\r\n")` for both docs; `git diff --stat` shows no deletions; content assertions pass.
- **Committed in:** `577139c` (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (1 blocking)
**Impact on plan:** None on deliverables — the encoding requirement was restored to a byte-exact CRLF-only state and the diff kept additive. No scope creep.

## Issues Encountered

- **The Edit tool did not preserve CRLF for the multi-line SETUP_GUIDE.txt insertion** (it did for the shorter README.md edit); handled as the blocking deviation above by normalizing the file back to CRLF-only. No content was lost.
- **Pre-existing suite cleanup noise** (`_FakeResponse.__del__` AttributeError from `test_llm_client.py`) still prints after the run; unrelated to this plan and out of scope. Suite reports `OK`.
- The untracked `audio/` directory pre-existed and was left untouched — not committed.

## Known Stubs

None — this plan changed documentation and added static tests only. No placeholder values, hardcoded empties, or unwired data sources.

## Threat Flags

None — no security-relevant surface beyond the plan's `<threat_model>`. T-09-04 (key baked into the image) is mitigated: BUILD.md forbids baking `app_config.json`, documents the host-directory mount, and `tests/test_docker_docs.py` asserts `ECHO_CONFIG_PATH=/config/app_config.json`. T-09-13 (unauthenticated LAN desktop) is mitigated by the loopback default plus `VNC_PASSWORD` for opt-in exposure. T-09-14 (http corporate base_url) is mitigated by the documented `https://` requirement. T-09-15 (opaque startup failure) is mitigated by the debugging section (app is the lifecycle anchor; `docker logs` shows the traceback).

## User Setup Required

None - no external service configuration required. The operator's live API key in the gitignored `app_config.json` was never read, printed, or committed; docs embed only a placeholder `sk-corp-...`.

## Next Phase Readiness

- **Ready for Plan 09-04** (build + browser E2E + mounted-config write round-trip): the docs now match the entrypoint defaults and the `ECHO_CONFIG_PATH` contract.
- **CNTR-04 is documented and test-guarded**, and the documentation half of CNTR-03 (mounted corporate endpoint) is in place.
- **Residual for verification:** `docker save`/`load` on a second PC remains the plan's manual verification item (owner: Plan 09-04 / operator).

---
*Phase: 09-containerized-gui-delivery*
*Completed: 2026-10-01*

## Self-Check: PASSED

- FOUND: BUILD.md
- FOUND: README.md
- FOUND: SETUP_GUIDE.txt
- FOUND: tests/test_docker_docs.py
- FOUND: .planning/phases/09-containerized-gui-delivery/09-03-SUMMARY.md
- FOUND commit: 0ba7e11 (Task 1)
- FOUND commit: 577139c (Task 2)
- FOUND commit: 2cd91c3 (Task 3)
- `py -3 -m unittest discover -s tests -p "test_docker_docs.py" -v` → Ran 15 tests, OK
- `py -3 -m unittest discover -s tests -v` → Ran 144 tests, OK
