# Phase 9 — Containerized GUI delivery: Research

**Researched:** 2026-10-01
**Domain:** Running a tkinter desktop GUI in a Docker container and viewing it in a browser (Xvfb + x11vnc + noVNC), bind-mounting configuration safely, and documenting offline deployment
**Confidence:** HIGH — every claim below was executed and observed in this workspace, not recalled

---

## Summary

Phase 9 makes the existing app runnable on another PC through **Docker Desktop**: the container
starts a virtual X display, runs the real `python -m echo` tkinter app on it, exposes that display
over VNC, and serves the noVNC browser client on **port 6080**. The corporate OpenAI-compatible
**https** endpoint is supplied through a **mounted config directory**, and the whole thing is
documented for `docker save` / `docker load` deployment.

The phase looks like "just add a VNC server", but two findings would otherwise burn the executor:

1. **A single-file bind mount (`-v app_config.json:/app/app_config.json`) breaks the app's
   "Save Settings".** `echo.config.save_config` writes atomically with `os.replace`, and `rename(2)`
   onto a bind-mounted file returns `EBUSY`. This was reproduced in this workspace
   (`OSError [Errno 16] Device or resource busy`). A **directory** mount works. Fix: add a small,
   behavior-preserving `ECHO_CONFIG_PATH` env override so the container can point the app at
   `/config/app_config.json` while the default (repo root) is unchanged.
2. **The VNC stack is fully automatable and was verified end-to-end** inside `python:3.14`
   (Debian 13 "trixie"): Xvfb + a real Tk window + x11vnc + websockify returned HTTP 200 for
   `/vnc.html` and a `101 Switching Protocols` for the WebSocket upgrade to x11vnc.

No new Python runtime dependency is added. The only Python change is the config-path override.

### Primary recommendation

| Requirement | Approach |
|-------------|----------|
| CNTR-01 | Install Debian `x11vnc` + `novnc` + `websockify` (already-available `xvfb`), serve `/usr/share/novnc/` on `6080` via `websockify --web`, browser opens `http://localhost:6080/vnc.html` |
| CNTR-02 | A `docker/entrypoint.sh` starts Xvfb → `python -m echo` → x11vnc (`-display :99 -localhost -rfbport 5900`) → websockify (`--web /usr/share/novnc/ 6080 localhost:5900`), with a `trap` for clean shutdown; `Dockerfile` switches `CMD` to it |
| CNTR-03 | `echo/config.py` gains `ECHO_CONFIG_PATH` (default unchanged) so a **directory** mount `-v <host_dir>:/config` + `ECHO_CONFIG_PATH=/config/app_config.json` works with the atomic writer; `validate_base_url` is untouched (https-only still enforced) |
| CNTR-04 | Expand `BUILD.md` with VNC run flags, volume mounts for config/audio/Whisper cache, and `docker save`/`docker load` (+ registry) deployment; add a README section and a SETUP_GUIDE mention |

---

## Environment (verified in this workspace)

| Fact | Value | How verified |
|------|-------|--------------|
| Docker | **29.8.1**, Docker Desktop (Linux containers), 15.17 GiB RAM | `docker version` / `docker info` |
| Base image | `python:3.14` = **Debian GNU/Linux 13 (trixie)** | `docker run --rm python:3.14 cat /etc/os-release` |
| tkinter in base image | **present** — Tk **8.6** | `docker run --rm python:3.14 python -c "import tkinter; print(tkinter.TkVersion)"` |
| Debian `x11vnc` | **0.9.17-1** (trixie/main) | `apt-cache policy x11vnc` in container |
| Debian `novnc` | **1:1.6.0-2** (trixie/main) | `apt-cache policy novnc` |
| Debian `websockify` | **0.12.0+dfsg1-4+b1** (trixie/main) | `apt-cache policy websockify` |
| Debian `xvfb` | **2:21.1.16-1.3+deb13u4** | `apt-cache policy xvfb` |
| Binary paths | `/usr/bin/Xvfb`, `/usr/bin/x11vnc`, `/usr/bin/websockify` | `which` in container |
| noVNC web root | `/usr/share/novnc/` with `vnc.html`, `vnc_lite.html`, `core/`, `app/`, `vendor/`, `utils/` | `ls /usr/share/novnc` |
| noVNC default WS path | `websockify` (`app/ui.js`: `UI.initSetting('path', 'websockify')`) | `grep` in container |
| Existing image | `echo:cpu` **already built** (5 GB disk / 1.18 GB content) — the current headless `xvfb-run` image | `docker images` |
| Free disk | `A:` **101.3 GB**, `C:` **6.6 GB** | `Get-PSDrive` |
| Whisper cache default | `os.path.join(os.getenv("XDG_CACHE_HOME", ~/.cache), "whisper")` → container `/root/.cache/whisper` | source of `openai-whisper==20250625` sdist |
| Current Dockerfile | headless `CMD ["xvfb-run", ... "python", "-m", "echo"]`, no VNC, no `EXPOSE` | `Dockerfile` read |
| `.dockerignore` | ignores `.planning/`, `app_config.json`, `build/`, `dist/`, `tests/__pycache__/` | `.dockerignore` read |

**Decision — Debian packages, not pip `websockify`/vendored noVNC.** The distro packages are pinned by
trixie, expose the canonical `/usr/share/novnc/vnc.html`, and avoid adding anything to the app's
`--require-hashes` lock. `websockify` already pulls its Python deps. This keeps Phase 8's supply-chain
guarantees intact.

**Decision — `python:3.14` (full), not `-slim`.** The full image already contains `_tkinter`
(`tkinter.TkVersion == 8.6`), which is the whole point of the phase; `-slim` would require building
Tk from source or a heavier `apt` layer.

---

## CNTR-01 — VNC GUI in the browser on `:6080` (VERIFIED END-TO-END)

### Verified probe (exact commands, run in a throwaway `python:3.14` container)

```bash
apt-get install -y --no-install-recommends novnc websockify x11vnc xvfb

export DISPLAY=:99
Xvfb :99 -screen 0 1280x800x24 -nolisten tcp &
# real Tk window created on the virtual display
python -c "import tkinter as tk; r=tk.Tk(); r.title('probe'); tk.Label(r,text='hello').pack(); r.update(); print('TK_WINDOW_OK'); r.destroy()"
x11vnc -display :99 -forever -shared -nopw -rfbport 5900 -bg -o /tmp/x11vnc.log
websockify --web /usr/share/novnc/ 6080 localhost:5900 &
```

Observed output:

```
TK_WINDOW_OK
PORT=5900
HTTP_VNC_HTML 200          # http://localhost:6080/vnc.html
HTTP_CORE 200              # http://localhost:6080/core/rfb.js
```

Second probe, the actual noVNC data channel (raw WebSocket upgrade handshake with stdlib sockets):

```
WS_UPGRADE_101 True
FIRST_LINE HTTP/1.1 101 Switching Protocols
# websockify log:
#   127.0.0.1 - - Plain non-SSL (ws://) WebSocket connection
#   127.0.0.1 - - connecting to: localhost:5900
```

**Conclusion:** exposed port `6080`, web root `/usr/share/novnc/`, and proxy target
`localhost:5900` are all confirmed. The browser URL required by the roadmap
(`http://localhost:6080/vnc.html`) serves the viewer, and the viewer's `/websockify`
endpoint upgrades and connects to x11vnc.

### Flags that matter

| Flag | Why |
|------|-----|
| `Xvfb :99 -screen 0 1280x800x24 -nolisten tcp` | Headless display; `-nolisten tcp` keeps the X socket local to the container |
| `x11vnc -display :99 -forever -shared` | `-forever` keeps serving after a client disconnects; `-shared` allows reconnect without restarting |
| `x11vnc -localhost -rfbport 5900` | Bind VNC to loopback only — `5900` is never exposed, only `6080` is; websockify connects over localhost inside the container |
| `x11vnc -nopw` (default) / `-passwd "$VNC_PASSWORD"` (optional) | Unauthenticated by default; a password can be supplied via env for non-localhost exposure |
| `websockify --web /usr/share/novnc/ 6080 localhost:5900` | Serves noVNC **and** proxies `/websockify` → x11vnc on one port |

### Window manager

**Not required.** The probe created and updated a real Tk window with no WM. Tk's own
`filedialog`/`messagebox` are drawn by Tk, not the window manager, so they work too. A WM
(`openbox`) could be added later for window decorations, but it is **out of scope**: it adds a
package for cosmetics only, consistent with this repo's "no dependency for cosmetics" stance
(Phase 5 decision: no `customtkinter`, no PyQt).

### Fonts / Cyrillic

Keep `fonts-dejavu` (already in the Dockerfile). The UI has Russian labels
(`echo/ui/*.py`), so a Cyrillic-capable font must remain in the image; `fonts-dejavu` covers it.

---

## CNTR-02 — Entrypoint (Xvfb → app → x11vnc → websockify)

### Design

A single `docker/entrypoint.sh` (`set -euo pipefail`) that:

1. exports `DISPLAY=:99` (overridable via `DISPLAY_NUM`, default `99`);
2. starts `Xvfb` and waits for `/tmp/.X11-unix/X99` to appear (bounded retry loop, not a fixed `sleep`);
3. starts `python -m echo` in the background, pointing at the mounted config
   (`ECHO_CONFIG_PATH=${ECHO_CONFIG_PATH:-/app/app_config.json}` — see CNTR-03);
4. starts `x11vnc -display :99 -localhost -rfbport 5900 -forever -shared` (with `-nopw`, or
   `-passwd "$VNC_PASSWORD"` when `VNC_PASSWORD` is set);
5. starts `websockify --web /usr/share/novnc/ 6080 localhost:5900`;
6. installs a `trap` on `INT`/`TERM` that terminates children, and exits the container when the app
   process exits (`wait "$APP_PID"`), so `docker stop` is clean.

### Why the app is the lifecycle anchor

The container should live exactly as long as the GUI process. If `python -m echo` crashes at
startup (e.g. missing display, bad config), the container exits and `docker logs` shows the traceback
— instead of a VNC port that silently serves an empty desktop.

### Why `-localhost` on x11vnc

Defence in depth: only `6080` is `EXPOSE`d, but binding VNC to loopback means that even a
mis-specified `-p 5900:5900` cannot reach the raw VNC server. websockify reaches it over
`localhost:5900` within the container network.

---

## CNTR-03 — Mounted config without weakening the https-only posture

### The trap: single-file bind mount breaks the atomic writer (REPRODUCED)

`echo/config.py` writes with `tempfile.mkstemp(dir=path.parent)` + `os.replace(tmp, path)`
(Phase 7 SEC-01). Reproduced in this workspace:

```
# -v A:\gsd-tmp\cfg.json:/app/app_config.json
FILE REPLACE_FAILED OSError [Errno 16] Device or resource busy:
    '/app/.app_config.x3raxr61.tmp' -> '/app/app_config.json'

# -v A:\gsd-tmp\cfgdir:/config   (directory mount)
DIR_REPLACE_OK {"llm":{"api_key":"y"}}
```

`rename(2)` over a bind-mounted file returns `EBUSY` because the file is a mount point. So the
naive `-v app_config.json:/app/app_config.json` would make **"Save Settings" fail every time** —
the endpoint could be read but never changed from the GUI.

### The fix: `ECHO_CONFIG_PATH` override (small, behavior-preserving)

Add to `echo/config.py`:

- a pure helper `resolve_config_path(env=None)` returning
  `Path(env["ECHO_CONFIG_PATH"])` when set, else the current
  `Path(__file__).resolve().parent.parent / "app_config.json"`;
- `CONFIG_PATH = resolve_config_path()` (module attribute, exactly as today).

Why this is safe:

- **Default is unchanged** — with no env var, `CONFIG_PATH` is byte-identical to today, so REFR-03
  (root `app_config.json`) and every existing test keep passing. `tests/test_config_read.py` and
  `test_config_write.py` monkey-patch `config.CONFIG_PATH` at runtime, which still works.
- **A directory mount + env var makes the atomic writer work** because `os.replace` then happens
  inside the mounted directory (`/config`), which is mutation-safe.
- **`validate_base_url` is untouched** — the corporate endpoint still must be `https://`
  (Phase 7 SEC-02). The mount changes *where the config lives*, never *what a valid URL is*.
- `_restrict_windows_acl` is a no-op on Linux (`os.name != "nt"`), so the 0600 mode path is the one
  exercised in the container.

### Corporate endpoint

The mounted `app_config.json` carries `llm.base_url` as an **https** OpenAI-compatible URL,
`llm.api_key`, `llm.model`, `llm.enabled`, `llm.summary_preset`. Because the app re-validates on
save, a corporate `http://` URL is rejected with the existing clear message — the security posture
is preserved by construction, not by documentation.

### Whisper model and audio

- Model: `whisper.load_model("base")` reads `~/.cache/whisper` (`/root/.cache/whisper`), matching
  upstream `openai-whisper` source verified above. A named volume or host bind keeps the ~142 MB
  model across runs and enables offline deployment on a PC without internet.
- Audio in / results out: the app's file dialogs start at `~` (`/root`) and let the user navigate.
  Bind a host directory (`-v <host>/audio:/root/audio`) and navigate to `/root/audio` in the
  dialog. Results are saved by the same dialog, so the mount must be read-write.

---

## CNTR-04 — Deployment on another PC

Recommended, verified-shape commands to document (not yet executed end-to-end — this is the
verification plan's job):

```powershell
# Build on the machine that has the sources
docker build -t echo:cpu .

# Run locally with a browser-visible GUI
docker run --rm -p 127.0.0.1:6080:6080 ^
  -v "$PWD\app_config.json" ... # ← NOT this: single-file mount breaks saves
  -v "${PWD}\config:/config" -e ECHO_CONFIG_PATH=/config/app_config.json ^
  -v echo-whisper:/root/.cache/whisper ^
  -v "${PWD}\audio:/root/audio" ^
  echo:cpu
# → http://localhost:6080/vnc.html
```

```powershell
# Move the image to another PC without a registry
docker save echo:cpu -o echo-cpu.tar      # multi-GB; use a drive with space (A: has 101 GB)
# ... copy echo-cpu.tar to the target PC ...
docker load -i echo-cpu.tar
```

**Deployment details to cover**

- **Port binding:** default docs use `-p 127.0.0.1:6080:6080` (loopback only). Exposing on the LAN
  (`-p 6080:6080`) is documented as opt-in **and** paired with setting `VNC_PASSWORD`, because
  noVNC/websockify here is plain `ws://` (no TLS).
- **Mounts:** config directory (`/config`), Whisper cache volume, audio directory. Never bake
  `app_config.json` into the image (it holds the API key; `.dockerignore` already excludes it).
- **GPU (optional, out of scope):** the image is CPU-only. A CUDA host would need
  `--gpus all` + `nvidia-container-toolkit` + the CUDA torch lock (`requirements-cuda.txt`); the
  docs should name this as the alternative path, not silently imply GPU support.
- **Image size:** the CPU image is ~1.18 GB compressed content (5 GB on disk after build). `docker
  save` output is multi-GB — document the disk requirement.

---

## Security

| Topic | Finding | Disposition |
|-------|---------|-------------|
| noVNC transport | `ws://` (no TLS) — VNC password, if used, is sent in cleartext over the Docker network | mitigate: default docs bind **127.0.0.1**; LAN exposure requires `VNC_PASSWORD`; TLS termination by the operator's reverse proxy is noted |
| Raw VNC port | x11vnc `-localhost` keeps `5900` on loopback inside the container | mitigate |
| Secret baked into image | `.dockerignore` excludes `app_config.json`; the Dockerfile never `COPY`s it | mitigate |
| Corporate endpoint scheme | `validate_base_url` still forces `https://`; the mount cannot bypass it | preserve (Phase 7 SEC-02) |
| Container runs as root | Xvfb/x11vnc as root inside the container; host impact limited by the container boundary | accept (local desktop tool; documented) |
| Untrusted audio input | audio is processed by whisper/ffmpeg in the container, same as the native app | accept (unchanged from the desktop threat model) |

---

## Validation Architecture

### Test infrastructure

| Property | Value |
|----------|-------|
| Framework | stdlib `unittest` (Python 3.14.3) — no new dependency (Phase 7/8 convention) |
| Config file | none — plain `tests/test_<subject>.py`, no `conftest.py`, no `tests/__init__.py` |
| Quick run command | `py -3 -m unittest discover -s tests -p "test_docker_delivery.py" -v` |
| Full suite command | `py -3 -m unittest discover -s tests -v` |
| Full-suite baseline | **106 tests** green after Phase 8 |
| Estimated runtime | quick ~1 s · full ~10–15 s (the `echo.ui.app` test imports `whisper`) |

### Feedback sampling

- **After every task commit:** the task's `<automated>` command (quick tier, ASCII-only)
- **After every plan wave:** full suite
- **Before `/gsd-verify-work`:** full suite green with the new tests, plus Plan 09-04's docker E2E
- **Max feedback latency:** ~30 s for the quick tier; the phase's docker build is a one-time
  multi-minute step owned by verification, not a sampling step

### Durable invariants (new tests)

- `tests/test_docker_delivery.py` — static, ASCII-only assertions on the delivered artifacts:
  `Dockerfile` installs `x11vnc`/`novnc`/`websockify` and `EXPOSE 6080`; `docker/entrypoint.sh`
  exists, contains `Xvfb`, `python -m echo`, `x11vnc`, `websockify`, `--web /usr/share/novnc/`,
  `-localhost`, a `trap`, and no `app_config.json` `COPY`; docs contain `vnc.html` and `6080`.
- `tests/test_config_env_override.py` — `resolve_config_path({})` equals the repo-root default;
  `resolve_config_path({"ECHO_CONFIG_PATH": "/config/app_config.json"})` returns that path; an
  existing `CONFIG_PATH`-monkey-patching test still works.

### Manual-only verification

| Behavior | Requirement | Why manual | Instructions |
|----------|-------------|-----------|--------------|
| The GUI is actually **visible** in the browser and the app is usable | CNTR-01, CNTR-02 | "Visible in a browser" is a human judgement; automation can only prove HTTP 200 + WS 101 | Build, run, open `http://localhost:6080/vnc.html`, confirm the Echo window renders, then select/transcribe/save |
| `docker save`/`load` on a second PC | CNTR-04 | Requires a second machine/Docker install | Follow BUILD.md on the target PC |

Everything else (image builds, container starts, `vnc.html` 200, WS upgrade 101, config round-trip,
save/load round-trip) is automated.

---

## Pitfalls

| # | Pitfall | Avoidance |
|---|---------|-----------|
| 1 | `-v app_config.json:/app/app_config.json` → `os.replace` fails with `EBUSY`, "Save Settings" breaks | Mount a **directory** at `/config` and set `ECHO_CONFIG_PATH=/config/app_config.json` |
| 2 | Baking `app_config.json` into the image leaks the API key | Keep it in `.dockerignore`; never `COPY` it; supply via mount/env |
| 3 | Starting x11vnc/websockify before Xvfb is ready → connection refused | Wait for `/tmp/.X11-unix/X99` (bounded loop) before starting the app/VNC |
| 4 | Container exits immediately (or never) because the wrong process is the lifecycle anchor | `wait` on the app PID; `trap` INT/TERM to kill children |
| 5 | Exposing `6080` on `0.0.0.0` without a password → open remote desktop | Default to `-p 127.0.0.1:6080:6080`; require `VNC_PASSWORD` for LAN exposure |
| 6 | expecting `localhost:6080/` to show the app | The viewer URL is `/vnc.html`; optionally `?autoconnect=1&resize=scale` |
| 7 | Re-downloading the Whisper model on every run | Mount `/root/.cache/whisper` as a named volume or host bind |
| 8 | Assuming the container sees host paths in the file dialog | Document that audio must be mounted and the dialog navigates container paths (`/root/audio`) |
| 9 | `docker build` re-installing CUDA torch (~10 GB) | Keep the existing CPU-wheel-first install layer; do not drop the `--index-url .../cpu` step |
| 10 | Editing `README.md` / `SETUP_GUIDE.txt` and losing UTF-8/CRLF | Read before edit; verify CRLF count and UTF-8 are unchanged (Phase 8 rule) |
| 11 | Non-ASCII literals on the PowerShell command line get mangled | Keep every `<automated>` command pure ASCII; put Russian assertions inside UTF-8 test files |
| 12 | `docker save` filling the system drive | Use `A:` (101 GB free); note the multi-GB artifact in the docs |

---

## Files touched by Phase 9

**New:** `docker/entrypoint.sh`, `tests/test_docker_delivery.py`, `tests/test_config_env_override.py`
**Edited:** `Dockerfile` (VNC packages, entrypoint, `EXPOSE 6080`, new `CMD`), `echo/config.py`
(`resolve_config_path` + `ECHO_CONFIG_PATH`), `BUILD.md`, `README.md`, `SETUP_GUIDE.txt`
**Unchanged:** the rest of `echo/**`, `main.py`, all lock files, `.dockerignore` (already correct)

---

## Sources

- noVNC README (server requirements, `novnc_proxy`, websockify) — https://github.com/novnc/noVNC
- websockify README (`--web` mini-webserver, WebSocket → TCP proxy) — https://github.com/novnc/websockify
- Debian 13 (trixie) package index — `x11vnc 0.9.17-1`, `novnc 1:1.6.0-2`, `websockify 0.12.0+dfsg1-4+b1`, `xvfb 2:21.1.16-1.3+deb13u4` (queried in-container)
- noVNC `app/ui.js` — default `path` setting `websockify`
- `openai-whisper==20250625` sdist — `whisper/__init__.py` model cache path (`XDG_CACHE_HOME` default `~/.cache/whisper`)
- Local reproductions in this workspace: Tk window on Xvfb, HTTP 200 `/vnc.html`, WS `101`, and the
  `EBUSY` single-file mount failure (Docker 29.8.1, Docker Desktop)
- `.planning/phases/08-supply-chain-hardening/08-RESEARCH.md` and `08-VALIDATION.md` (test conventions)
