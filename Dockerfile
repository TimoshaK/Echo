FROM python:3.14

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    DEBIAN_FRONTEND=noninteractive

# ffmpeg (Whisper) + Tk libraries + fonts (Cyrillic) + the VNC stack that makes the
# GUI visible in a browser (Xvfb -> x11vnc -> noVNC/websockify).
RUN apt-get update && apt-get install -y --no-install-recommends \
        ffmpeg \
        tk \
        xvfb \
        x11vnc \
        novnc \
        websockify \
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
RUN pip install --upgrade pip \
 && pip install --index-url https://download.pytorch.org/whl/cpu torch==2.14.0 \
 && pip install --require-hashes -r requirements.txt

COPY echo ./echo
COPY main.py ./

# GUI delivery: entrypoint starts Xvfb, the app, x11vnc and noVNC (websockify).
COPY docker/entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh

# noVNC web client + WebSocket proxy (http://localhost:6080/vnc.html).
EXPOSE 6080

ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
