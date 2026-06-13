#!/usr/bin/env bash
# start-api.sh
# Starts (or restarts) the Workbench API server.

source "$(dirname "${BASH_SOURCE[0]}")/load-config.sh"

# WORKBENCH_DIR and API_PORT come from config.json via load-config.sh.
PIDFILE="/tmp/workbench-api.pid"
LOGFILE="$WORKBENCH_DIR/data/api.log"
API_PY="$WORKBENCH_DIR/api.py"

# Kill existing instance if running
if [[ -f "$PIDFILE" ]]; then
    OLD_PID=$(cat "$PIDFILE")
    if kill -0 "$OLD_PID" 2>/dev/null; then
        echo "Stopping existing API server (PID $OLD_PID)..."
        kill "$OLD_PID"
        sleep 1
    fi
    rm -f "$PIDFILE"
fi

echo "Starting Workbench API server..."
nohup python3 "$API_PY" >> "$LOGFILE" 2>&1 &
echo $! > "$PIDFILE"
sleep 0.5

if kill -0 "$(cat "$PIDFILE")" 2>/dev/null; then
    echo "API server running (PID $(cat "$PIDFILE")) → http://127.0.0.1:${API_PORT}"
    echo "Log: $LOGFILE"
else
    echo "ERROR: API server failed to start. Check $LOGFILE"
    exit 1
fi
