#!/bin/bash
set -e

LOGDIR="/tmp/super-logs"
mkdir -p "$LOGDIR"

cleanup() {
    echo "Stopping..."
    kill $API_PID $CF_PID 2>/dev/null
    exit 0
}
trap cleanup SIGINT SIGTERM

restart_api() {
    while true; do
        echo "[API] Starting..."
        python /workspaces/Super/main.py >> "$LOGDIR/api.log" 2>&1 &
        API_PID=$!
        wait $API_PID
        echo "[API] Crashed (exit $?), restarting in 2s..."
        sleep 2
    done
}

restart_tunnel() {
    while true; do
        echo "[Tunnel] Starting..."
        /workspaces/Super/cloudflared tunnel --url http://localhost:8000 \
            --logfile "$LOGDIR/tunnel.log" 2>&1 &
        CF_PID=$!
        wait $CF_PID
        echo "[Tunnel] Crashed (exit $?), restarting in 2s..."
        sleep 2
    done
}

# Wait for API to be ready before starting tunnel
restart_api &
sleep 3

restart_tunnel &
wait
