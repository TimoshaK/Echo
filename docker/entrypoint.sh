#!/usr/bin/env bash
# Echo container entrypoint: Xvfb -> python -m echo -> x11vnc -> noVNC (websockify).
# The browser reaches the GUI at http://<host>:6080/vnc.html.
set -euo pipefail

DISPLAY_NUM="${DISPLAY_NUM:-99}"
SCREEN="${SCREEN:-1440x900x24}"
VNC_PORT="${VNC_PORT:-5900}"
NOVNC_PORT="${NOVNC_PORT:-6080}"
export DISPLAY=":${DISPLAY_NUM}"

# 1. Virtual X display (local socket only).
Xvfb "$DISPLAY" -screen 0 "$SCREEN" -nolisten tcp &
XVFB_PID=$!

# 2. Wait for the X socket before anything tries to talk to it.
for _ in $(seq 1 50); do
    [ -e "/tmp/.X11-unix/X${DISPLAY_NUM}" ] && break
    sleep 0.1
done

# 3. The application. It is the lifecycle anchor: when it exits, the container exits.
python -m echo &
APP_PID=$!

# 4. VNC server, bound to loopback only (only 6080 is exposed).
VNC_ARGS=(-display "$DISPLAY" -forever -shared -localhost -rfbport "$VNC_PORT" -o /tmp/x11vnc.log)
if [ -n "${VNC_PASSWORD:-}" ]; then
    VNC_ARGS+=(-passwd "$VNC_PASSWORD")
else
    VNC_ARGS+=(-nopw)
fi
x11vnc "${VNC_ARGS[@]}" &
X11VNC_PID=$!

# 5. noVNC web client + WebSocket proxy on the exposed port.
websockify --web /usr/share/novnc/ "$NOVNC_PORT" "localhost:${VNC_PORT}" &
WS_PID=$!

# 6. Clean shutdown on `docker stop`.
shutdown() {
    kill -TERM "$APP_PID" "$X11VNC_PID" "$WS_PID" "$XVFB_PID" 2>/dev/null || true
    wait 2>/dev/null || true
}
trap shutdown INT TERM

# 7. Follow the app; propagate its exit code.
wait "$APP_PID"
