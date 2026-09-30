FROM python:3.14

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    DEBIAN_FRONTEND=noninteractive

# ffmpeg (нужен Whisper) + библиотеки для Tkinter + шрифты (кириллица) + xvfb (на случай headless)
RUN apt-get update && apt-get install -y --no-install-recommends \
        ffmpeg \
        tk \
        xvfb \
        xauth \
        fonts-dejavu \
        libx11-6 libxext6 libxrender1 libsm6 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Dependency layer (separate for better rebuild caching).
COPY requirements.txt ./
# PyPI's torch==2.14.0 for Linux is the CUDA build, which drags in the whole
# nvidia-*/cuda-toolkit stack (~10 GB). For a small CPU image, install the CPU
# wheel from the PyTorch CPU index first; requirements.txt then sees torch as
# already satisfied and hash-checks everything else (triton is pinned with a
# Linux marker in the lock).
# NOTE: torch itself is installed here WITHOUT hash verification, because the
# hashed lock pins the Windows wheel. To hash-verify torch too, regenerate a
# Linux CPU lock with `pip-compile --index-url https://download.pytorch.org/whl/cpu`.
# TODO: generate that Linux CPU lock and switch this layer to it.
RUN pip install --upgrade pip \
 && pip install --index-url https://download.pytorch.org/whl/cpu torch==2.14.0 \
 && pip install --require-hashes -r requirements.txt

COPY echo ./echo
COPY main.py ./

# GUI needs an X display. xvfb-run provides a virtual one so the app starts
# headlessly; the window is not visible. For a visible/interactive GUI add a VNC
# server (x11vnc + noVNC) or use X11 forwarding.
CMD ["xvfb-run", "-a", "-s", "-screen 0 1280x800x24", "python", "-m", "echo"]