#!/usr/bin/env bash
# start-api.sh
# Starts (or restarts) the Workbench API server on port 8081.

PIDFILE="/tmp/workbench-api.pid"
LOGFILE="/var/www/html/workbench/data/api.log"
API_PY="/var/www/html/workbench/api.py"

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
    echo "API server running (PID $(cat "$PIDFILE")) → http://127.0.0.1:8081"
    echo "Log: $LOGFILE"
else
    echo "ERROR: API server failed to start. Check $LOGFILE"
    exit 1
fi
