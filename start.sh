#!/bin/bash

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOGDIR="/tmp/super-logs"
mkdir -p "$LOGDIR"

# Download cloudflared binary if not present
CF_BIN="$SCRIPT_DIR/cloudflared"
if [ ! -f "$CF_BIN" ]; then
    echo "[Setup] Downloading cloudflared..."
    curl -fsSL "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64" -o "$CF_BIN"
    chmod +x "$CF_BIN"
    echo "[Setup] cloudflared downloaded."
fi

API_PID=""
CF_PID=""

cleanup() {
    echo "Stopping..."
    [[ -n "$API_PID" ]] && kill "$API_PID" 2>/dev/null
    [[ -n "$CF_PID" ]] && kill "$CF_PID" 2>/dev/null
    exit 0
}
trap cleanup SIGINT SIGTERM

restart_api() {
    while true; do
        echo "[API] Starting..."
        cd "$SCRIPT_DIR"
        python main.py >> "$LOGDIR/api.log" 2>&1 &
        API_PID=$!
        echo "[API] PID=$API_PID running on port ${PORT:-8000}"
        wait $API_PID
        echo "[API] Exited (code $?), restarting in 3s..."
        sleep 3
    done
}

restart_tunnel() {
    while true; do
        echo "[Tunnel] Starting..."
        "$CF_BIN" tunnel --url "http://localhost:${PORT:-8000}" \
            >> "$LOGDIR/tunnel.log" 2>&1 &
        CF_PID=$!
        wait $CF_PID
        echo "[Tunnel] Exited (code $?), restarting in 3s..."
        sleep 3
    done
}

# Pings health every 4 minutes to prevent inactivity shutdown
keep_alive() {
    sleep 20
    while true; do
        curl -sf "http://localhost:${PORT:-8000}/health" > /dev/null 2>&1 || true
        sleep 240
    done
}

restart_api &
sleep 5
restart_tunnel &
keep_alive &

wait
