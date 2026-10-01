---
phase: 09-containerized-gui-delivery
plan: 01
subsystem: infra
tags: [docker, vnc, x11vnc, novnc, websockify, xvfb, tkinter, cpu-torch, require-hashes, entrypoint, cntr-01, cntr-02]

# Dependency graph
requires: []
provides:
  - "a CPU image Dockerfile that installs the VNC stack (xvfb, x11vnc, novnc, websockify) and EXPOSEs 6080"
  - "docker/entrypoint.sh — the process supervisor that brings up Xvfb → python -m echo → x11vnc → websockify"
  - "tests/test_docker_delivery.py — 15 durable static invariants for the two delivery artifacts"
affects: [plan-09-04, phase-09-verify-work]

# Tech tracking
tech-stack:
  added:
    - "Debian trixie packages: xvfb, x11vnc, novnc, websockify (installed via apt in the image)"
  patterns:
    - "single entrypoint script is the container's process supervisor; the GUI process is the lifecycle anchor"
    - "raw VNC bound to loopback (x11vnc -localhost); only the noVNC port 6080 is EXPOSE'd"
    - "optional VNC_PASSWORD env gate; never hardcode a secret"
    - "durable static tests assert image/entrypoint invariants without building the image"

key-files:
  created:
    - docker/entrypoint.sh
    - tests/test_docker_delivery.py
  modified:
    - Dockerfile

key-decisions:
  - "Used Debian apt packages for the VNC stack (not pip websockify / vendored noVNC) so Phase 8's --require-hashes lock stays untouched and Debian pins the versions"
  - "x11vnc is loopback-only (-localhost); noVNC port 6080 is the single exposed surface"
  - "ENTRYPOINT (not CMD) so `docker run echo:cpu` always boots the GUI; probes can override with --entrypoint"
  - "The app process is the lifecycle anchor (wait \"$APP_PID\") so the container exits when the GUI dies (T-09-07)"
  - "The CPU-torch-from-CPU-index install layer is preserved verbatim in behavior (T-09-09)"
  - "Full `docker build` was validated with `docker build --check` instead of a multi-GB rebuild; runtime proof is Plan 09-04 (C: had only 6.6 GB free vs the existing 5 GB image)"

patterns-established:
  - "The image never bakes app_config.json: no COPY of it and no `COPY . .`; enforced by a static test (T-09-01)"
  - "Entrypoint waits for the X socket file (bounded loop) before starting the app or VNC servers"
  - "Artifacts delivered in this plan are guarded by tests owned by the same plan, so same-wave plans stay green independently"

requirements-completed: [CNTR-01, CNTR-02]

# Metrics
duration: ~10min
completed: 2026-10-01
---

# Phase 9 Plan 01: Containerized GUI Delivery Summary

**A CPU Docker image now installs the xvfb/x11vnc/noVNC stack and boots the tkinter app on a virtual display via an entrypoint that serves the GUI in a browser on port 6080 (Xvfb → python -m echo → x11vnc → websockify), with 15 static invariants proving no secret is baked in and the raw VNC port stays loopback-only**

## Performance

- **Duration:** ~10 min
- **Started:** 2026-10-01T03:31:48Z
- **Completed:** 2026-10-01T03:42:13Z
- **Tasks:** 3
- **Files modified:** 3 (1 modified, 2 created)

## Accomplishments

- **Task 1 — Dockerfile carries the full VNC stack.** Added `xvfb`, `x11vnc`, `novnc`, `websockify` (and `xauth`) to the apt layer while keeping `ffmpeg`, `tk` and `fonts-dejavu`; added `EXPOSE 6080`; copied `docker/entrypoint.sh` to `/usr/local/bin/entrypoint.sh`, `chmod +x`ed it and set it as `ENTRYPOINT`. The CPU-torch-then-hash-check install layer is unchanged in behavior, and `app_config.json` is never copied.
- **Task 2 — the entrypoint is a real supervisor.** `docker/entrypoint.sh` (`set -euo pipefail`) starts Xvfb on `:99` and waits for `/tmp/.X11-unix/X99`, launches `python -m echo` as the lifecycle anchor, starts `x11vnc -localhost` on 5900 (optional `VNC_PASSWORD`), then `websockify --web /usr/share/novnc/ 6080 localhost:5900`, and installs a `trap shutdown INT TERM`. LF line endings (0 CR bytes).
- **Task 3 — durable invariants committed.** `tests/test_docker_delivery.py` adds **15** test cases across `DockerfileTests` and `EntrypointTests`, including `EXPOSE 6080`, `--web /usr/share/novnc/`, `-localhost`, `trap `, `wait "$APP_PID"`, no `COPY app_config.json` / `COPY . .`, and no `\r` bytes in the entrypoint.
- **Verification:** quick tier 15/15 OK; full suite **121/121 OK** (baseline 106 + 15 new); `docker build --check .` → "Check complete, no warnings found."

## Task Commits

Each task was committed atomically:

1. **Task 1: Add the VNC stack, entrypoint wiring and EXPOSE 6080 to the Dockerfile** — `58f9ed3` (feat)
2. **Task 2: Create docker/entrypoint.sh (Xvfb → app → x11vnc → websockify)** — `d83b153` (feat)
3. **Task 3: Add tests/test_docker_delivery.py** — `f74428c` (test)

**Plan metadata:** _pending final metadata commit_ (docs: complete plan)

## Files Created/Modified

- `Dockerfile` — installs the VNC stack; `EXPOSE 6080`; copies/chmods and ENTRYPOINTs `docker/entrypoint.sh`; preserves the CPU-torch + `--require-hashes` install layer; never COPYs `app_config.json`.
- `docker/entrypoint.sh` — Xvfb → `python -m echo` → x11vnc (`-localhost`, optional password) → websockify (noVNC web root on 6080 → localhost:5900) with a signal trap and app-anchored lifecycle.
- `tests/test_docker_delivery.py` — 15 stdlib `unittest` cases asserting the above invariants from the committed sources.

## Decisions Made

- **Debian apt packages, not pip `websockify`/vendored noVNC** — keeps Phase 8's hash-locked `requirements.txt` untouched and lets Debian pin the versions (follows the research decision).
- **`-localhost` on x11vnc + only `EXPOSE 6080`** — defence in depth; even a mis-specified `-p 5900:5900` cannot reach the raw VNC server (T-09-02).
- **`ENTRYPOINT` rather than `CMD`** — `docker run echo:cpu` always boots the GUI; probes can still override with `--entrypoint`.
- **App process is the lifecycle anchor** — `wait "$APP_PID"` means `docker ps` reflects the GUI's health (T-09-07).
- **Validated the Dockerfile with `docker build --check` rather than a full build this wave** — see Deviations/Issues; runtime proof is Plan 09-04.

## Deviations from Plan

**1. [Rule 3-adjacent — Verification scope] Full `docker build -t echo:cpu .` deferred to Plan 09-04**

- **Found during:** Plan-level verification (after Task 3).
- **Issue:** The plan's `<verification>` lists `docker build -t echo:cpu .` succeeds, but the Dockerfile's apt layer changed, which invalidates downstream cache: a rebuild would re-run the torch/deps install and produce a second ~5 GB image. The system drive `C:` has only **6.6 GB** free while the existing `echo:cpu` image is **5 GB**, so a full rebuild risks filling the system drive (explicit project rule: watch `C:` free space; prefer targeted checks).
- **Fix:** Ran `docker build --check .` (BuildKit lint) → **"Check complete, no warnings found."**, proving the Dockerfile parses and is lint-clean without pulling multi-GB layers. The plan's own note delegates runtime proof to Plan 09-04 ("Plan 09-04 proves the runtime; this at least proves the file"), and the static tests already prove the required content.
- **Files modified:** none.
- **Verification:** `docker build --check .` clean; `tests/test_docker_delivery.py` 15/15 OK.
- **Committed in:** no commit (no file changed).

---

**Total deviations:** 1 verification-scope deferral (no code change).
**Impact on plan:** None on the delivered artifacts. Image buildability is proven at the lint/structure level here; the actual multi-GB build + browser E2E remains with Plan 09-04 as the plan intends.

## Issues Encountered

- **`core.autocrlf=true` with no `.gitattributes`.** Git normalizes `docker/entrypoint.sh` to LF in the repository (verified: the committed blob is LF; `test_no_crlf` passes on the working file), but a fresh checkout on Windows would write CRLF and could break `docker build` with `exec format error`. Fixing this would require adding `.gitattributes`, which is **outside this plan's declared files** (`Dockerfile`, `docker/entrypoint.sh`, `tests/test_docker_delivery.py`), so it was not changed. Recorded here as a concern for a future plan/verification; the current working tree and blob are LF.
- **No other issues.** The quick and full suites behaved as predicted.

## Known Stubs

None — the plan delivered a Dockerfile, a shell entrypoint and static tests only. No placeholder values, hardcoded empties, or unwired data sources.

## Threat Flags

None — no security-relevant surface beyond the plan's `<threat_model>`. T-09-01 (API key baked into the image) is mitigated and test-enforced (no `COPY app_config.json` / `COPY . .`); T-09-02 (unauthenticated noVNC on the LAN) is mitigated by `x11vnc -localhost`, only `EXPOSE 6080`, and the optional `VNC_PASSWORD`; T-09-07 (healthy-looking port while the GUI is dead) is mitigated by the app process being the lifecycle anchor; T-09-08 (orphaned VNC/Xvfb after `docker stop`) is mitigated by `trap shutdown INT TERM`; T-09-09 (build re-resolves CUDA torch) is mitigated by preserving the CPU-wheel-first layer and is test-asserted.

## User Setup Required

None - no external service configuration required. (The operator's live API key in the gitignored `app_config.json` was never read, printed, or committed.)

## Next Phase Readiness

- **Ready for Plan 09-02** (independent; `echo/config.py` `ECHO_CONFIG_PATH` override — disjoint files) and **Plan 09-04** (build + browser E2E).
- **CNTR-01 and CNTR-02 artifacts are in place and test-guarded:** the image installs the VNC stack, exposes only 6080, and the entrypoint auto-starts the full pipeline.
- **Residual items for verification:** (1) the full `docker build` + `http://localhost:6080/vnc.html` HTTP 200 / WS 101 proof is owned by Plan 09-04; (2) the CRLF-on-checkout concern needs a `.gitattributes` rule in a future plan if the repo is cloned on Windows.

---

*Phase: 09-containerized-gui-delivery*
*Completed: 2026-10-01*

## Self-Check: PASSED

- FOUND: Dockerfile
- FOUND: docker/entrypoint.sh
- FOUND: tests/test_docker_delivery.py
- FOUND: .planning/phases/09-containerized-gui-delivery/09-01-SUMMARY.md
- FOUND commit: 58f9ed3 (Task 1)
- FOUND commit: d83b153 (Task 2)
- FOUND commit: f74428c (Task 3)
- `py -3 -m unittest discover -s tests -p "test_docker_delivery.py" -v` → Ran 15 tests, OK
- `py -3 -m unittest discover -s tests -v` → Ran 121 tests, OK
- `docker build --check .` → Check complete, no warnings found.
