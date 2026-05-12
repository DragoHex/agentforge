#!/usr/bin/env bash
# start-server.sh — build and start the workbench Go server on port 1337.

set -euo pipefail

# Always use the Apache-served canonical location so the server writes
# to the same directory that the browser fetches data from.
WORKBENCH_DIR="/var/www/html/workbench"
SERVER_DIR="$WORKBENCH_DIR/server"
BINARY="$SERVER_DIR/workbench-server"
PIDFILE="/tmp/workbench-server.pid"
LOGFILE="$WORKBENCH_DIR/data/server.log"

# Kill any existing instance
if [[ -f "$PIDFILE" ]]; then
    OLD_PID=$(cat "$PIDFILE")
    if kill -0 "$OLD_PID" 2>/dev/null; then
        echo "Stopping existing server (PID $OLD_PID)..."
        kill "$OLD_PID"
        sleep 1
    fi
    rm -f "$PIDFILE"
fi

# Build
echo "Building Go server..."
cd "$SERVER_DIR"
go build -o "$BINARY" .

mkdir -p "$WORKBENCH_DIR/data"

# Start
echo "Starting workbench server on port 1337..."
nohup "$BINARY" >> "$LOGFILE" 2>&1 &
echo $! > "$PIDFILE"
sleep 0.5

if kill -0 "$(cat "$PIDFILE")" 2>/dev/null; then
    echo "Server running (PID $(cat "$PIDFILE")) → http://127.0.0.1:1337"
    echo "Log: $LOGFILE"
else
    echo "ERROR: Server failed to start. Check $LOGFILE"
    exit 1
fi
