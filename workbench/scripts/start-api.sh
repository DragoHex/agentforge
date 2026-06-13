#!/usr/bin/env bash
# start-api.sh
# Starts (or restarts) the unified Workbench server (server.py).
# Replaces both api.py (port 8081) and start-server.sh (Go, port 1337).

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKBENCH_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
SERVER_PY="$WORKBENCH_DIR/server.py"
SERVER_PORT=8000
PIDFILE="/tmp/workbench-api.pid"
LOG_DIR="$HOME/.config/workbench"
LOGFILE="$LOG_DIR/server.log"

mkdir -p "$LOG_DIR"

# Kill existing instance if running
if [[ -f "$PIDFILE" ]]; then
    OLD_PID=$(cat "$PIDFILE")
    if kill -0 "$OLD_PID" 2>/dev/null; then
        echo "Stopping existing server (PID $OLD_PID)..."
        kill "$OLD_PID"
        sleep 1
    fi
    rm -f "$PIDFILE"
fi

echo "Starting Workbench server on port $SERVER_PORT..."
nohup python3 "$SERVER_PY" "$SERVER_PORT" >> "$LOGFILE" 2>&1 &
echo $! > "$PIDFILE"
sleep 0.5

if kill -0 "$(cat "$PIDFILE")" 2>/dev/null; then
    echo "Server running (PID $(cat "$PIDFILE")) → http://127.0.0.1:${SERVER_PORT}"
    echo "Log: $LOGFILE"
else
    echo "ERROR: Server failed to start. Check $LOGFILE"
    exit 1
fi
