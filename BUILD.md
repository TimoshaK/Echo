# Building and running the Echo Docker image

This image runs the real tkinter GUI (`python -m echo`) on a virtual X display and
serves it to your browser through `x11vnc` + noVNC. **Open the GUI at:**

```text
http://localhost:6080/vnc.html
```

The same image is also portable: `docker save` it on the build machine, copy the tar
to another PC, `docker load` it there, and run it with the same mounts. No Python,
torch or FFmpeg install is needed on the target PC.

The image is **CPU-only**. It installs `ffmpeg`, Tk, the VNC stack
(`xvfb`, `x11vnc`, `novnc`, `websockify`) and a Cyrillic-capable font.

## Build

```powershell
docker build -t echo:cpu .
```

## Run — browser GUI (recommended)

Use a single line so the command behaves the same in PowerShell and bash (no
line-continuation anchors to get wrong):

```powershell
docker run --rm -p 127.0.0.1:6080:6080 -v "${PWD}/config:/config" -e ECHO_CONFIG_PATH=/config/app_config.json -v echo-whisper:/root/.cache/whisper -v "${PWD}/audio:/root/audio" echo:cpu
```

Then open <http://localhost:6080/vnc.html>. Optionally append
`?autoconnect=1&resize=scale` so the viewer connects immediately and scales the
desktop to the browser window.

The command above:

- binds the noVNC port to **loopback only** (`-p 127.0.0.1:6080:6080`);
- mounts the host `config/` directory at `/config` and points the app at it with
  `ECHO_CONFIG_PATH`;
- keeps the downloaded Whisper model in the named volume `echo-whisper`;
- mounts the host `audio/` directory at `/root/audio` for input and results.

Create the host directories first if they do not exist:

```powershell
mkdir config, audio
```

## Port binding and security

- **Default is machine-local.** `-p 127.0.0.1:6080:6080` publishes the GUI on
  `localhost` only; nobody on the LAN can reach it.
- **Exposing on the LAN is opt-in.** Use `-p 6080:6080` (all interfaces) *only*
  together with a VNC password:

  ```powershell
  docker run --rm -p 6080:6080 -e VNC_PASSWORD=<password> -v "${PWD}/config:/config" -e ECHO_CONFIG_PATH=/config/app_config.json -v echo-whisper:/root/.cache/whisper -v "${PWD}/audio:/root/audio" echo:cpu
  ```

- **No TLS here.** noVNC/websockify serves plain `ws://`, so a VNC password travels
  in cleartext on the wire. If the GUI must leave the machine, terminate TLS at a
  reverse proxy (e.g. nginx/Caddy) in front of `127.0.0.1:6080` and keep the
  published port loopback-only.
- **The raw VNC port is not reachable.** `x11vnc` is bound to loopback *inside* the
  container (`-localhost`); only `6080` is `EXPOSE`d. A stray `-p 5900:5900` would
  still not reach the VNC server.
- `VNC_PASSWORD` is only read from the environment at run time and is never baked
  into the image.

## Configuration (corporate https LLM)

The app reads its settings from `app_config.json`. In a container, supply that file
through a **mounted directory**:

1. Create `app_config.json` inside the host `config/` directory.
2. Mount the directory (`-v "${PWD}/config:/config"`) and set
   `-e ECHO_CONFIG_PATH=/config/app_config.json` (already in the run command above).

Example `config/app_config.json` for a corporate OpenAI-compatible endpoint:

```json
{
  "llm": {
    "api_key": "sk-corp-...",
    "base_url": "https://llm.corp.example/v1",
    "model": "gpt-4o-mini",
    "enabled": true,
    "summary_preset": "free"
  }
}
```

- `base_url` **must** be `https://`. The app validates the scheme and rejects
  `http://` (or any non-https scheme) with a clear message — this is enforced by the
  application, not just by this document.
- **Do NOT mount the config file itself.**
  `-v app_config.json:/app/app_config.json` is **wrong**: the app saves settings
  atomically with `os.replace`, and renaming over a bind-mounted *file* fails with
  `EBUSY`. "Save Settings" would break every time. Mount the **directory** instead
  (as shown) so the atomic write happens inside the mounted directory.
- **Never bake the key into the image.** `.dockerignore` excludes `app_config.json`,
  and the Dockerfile never copies it. The API key lives only in the host directory
  the operator mounts.

## Audio and results

The app's file dialogs start at `/root` and let you navigate. Mount a host directory
at `/root/audio` (as in the run command) and choose files from `/root/audio`:

- The mount is **read-write**: transcription results (`.txt`/`.srt`) are saved through
  the same dialog, back into `/root/audio`.
- A read-only mount would let you select input but not save output.

## Whisper model cache

Whisper stores the `base` model in `~/.cache/whisper` — inside the container that is
`/root/.cache/whisper`. Mount it so the ~142 MB model is downloaded only once:

- **Named volume** (recommended, as in the run command): `-v echo-whisper:/root/.cache/whisper`.
- **Host directory**: `-v "${PWD}/whisper-cache:/root/.cache/whisper"`.

Once the cache is populated, transcription works **without internet** access.

## Deploy to another PC

Two supported paths.

### 1. Without a registry — `docker save` / `docker load`

On the machine that built the image:

```powershell
docker save echo:cpu -o echo-cpu.tar
```

Copy `echo-cpu.tar` to the target PC, then:

```powershell
docker load -i echo-cpu.tar
```

Notes:

- The tar is **multi-GB** (the on-disk image is ~5 GB). Save it to a drive with free
  space — `A:` had 101 GB free at research time. Avoid the system drive.
- The target PC needs **Docker Desktop** (with Linux containers) plus the same mounts
  (`config/`, `audio/`, and the Whisper cache volume/dir).

### 2. With a registry

```powershell
docker tag echo:cpu <registry>/echo:cpu
docker push <registry>/echo:cpu
# on the target PC:
docker pull <registry>/echo:cpu
```

## Optional GPU

This image is **CPU-only**. It works on any host without a GPU. Running on an NVIDIA
GPU is possible but out of scope for this image: it needs a CUDA host,
`--gpus all`, the `nvidia-container-toolkit`, and the `requirements-cuda.txt` lock
(`torch==2.14.0+cu130`). Building that variant is a separate task; do not assume this
image uses the GPU.

## Debugging

- Open a shell in the image (overriding the entrypoint):

  ```powershell
  docker run --rm --entrypoint bash echo:cpu
  ```

- Read the startup logs of a running container:

  ```powershell
  docker logs <container-name>
  ```

- The **app process is the lifecycle anchor**: the entrypoint runs `python -m echo` and
  waits on it. If the app crashes at startup (bad config, missing display), the
  container exits and the traceback is in `docker logs` — rather than a VNC port that
  silently serves an empty desktop.

## How dependencies are installed

`requirements.txt` is a **pip-tools lock generated on Windows**. On Linux, PyPI's
`torch==2.14.0` is the **CUDA** build, which pulls the entire `nvidia-*` /
`cuda-toolkit` stack (~10 GB). To keep this a small CPU image, the Dockerfile:

1. installs the CPU wheel from the PyTorch CPU index,
   `pip install --index-url https://download.pytorch.org/whl/cpu torch==2.14.0`,
2. then `pip install --require-hashes -r requirements.txt` — torch is already
   satisfied, and everything else (including `triton`) is hash-checked.

**`triton`**: it is a Linux-only transitive dependency of `openai-whisper`
(`triton>=2; platform_machine == "x86_64" and sys_platform == "linux"`). It has no
Windows wheel, so a Windows-generated lock omits it; it is therefore pinned in
`requirements.txt`/`requirements-cuda.txt` with an explicit **Linux marker** and
its sha256 hashes (Linux x86_64, cp310–cp314). On Windows the marker is false and
pip skips it.

> **Known limitation:** `torch` is installed in the image **without** hash
> verification, because the hashed lock pins the Windows wheel. Everything else is
> hash-checked.

## Regenerating the locks

Locks are compiled with pip-tools inside the target OS — **never cross-compile**
(pip-tools does not support it; a Windows lock misses Linux-only deps such as
`triton`).

Windows lock (CPU):

```powershell
CUSTOM_COMPILE_COMMAND="pip-compile --generate-hashes --allow-unsafe --strip-extras --no-emit-index-url --no-emit-trusted-host --output-file requirements.txt requirements.in" `
  py -3 -m piptools compile --generate-hashes --allow-unsafe --strip-extras --no-emit-index-url --no-emit-trusted-host --output-file requirements.txt requirements.in
```

To produce a fully hash-verified **Linux CPU** lock (recommended future step —
this would let the Dockerfile drop the separate torch install and hash-verify
torch too), run the compile inside `python:3.14` against the PyTorch CPU index:

```bash
docker run --rm -v "$PWD":/work -w /work python:3.14 bash -lc '
  pip install pip-tools &&
  pip-compile --generate-hashes --allow-unsafe --strip-extras \
      --index-url https://download.pytorch.org/whl/cpu \
      --extra-index-url https://pypi.org/simple \
      --output-file requirements-linux.txt requirements.in
'
```

Then switch the Dockerfile to `pip install --require-hashes -r requirements-linux.txt`.

> Do **not** run a plain (PyPI) Linux compile of this project: it resolves the
> CUDA torch and downloads tens of GB of `nvidia-*`/`cuda-toolkit` wheels.
