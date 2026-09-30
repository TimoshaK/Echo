# Building the Docker (CPU) image

```powershell
docker build -t echo:cpu .
docker run --rm -it echo:cpu            # runs the GUI under xvfb (headless; window not visible)
```

The image runs `python -m echo` under `xvfb-run`, which provides a **virtual** X
display. The window is created but not visible; for an interactive GUI add a VNC
server (`x11vnc` + `noVNC`) or use X11 forwarding.

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
