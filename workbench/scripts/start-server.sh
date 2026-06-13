#!/usr/bin/env bash
# start-server.sh — build and start the workbench Go server.

set -euo pipefail

source "$(dirname "${BASH_SOURCE[0]}")/load-config.sh"

# WORKBENCH_DIR and SERVER_PORT come from config.json via load-config.sh.
# The server always uses the Apache-served canonical location so it writes
# to the same directory that the browser fetches data from.
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
echo "Starting workbench server on port ${SERVER_PORT}..."
nohup "$BINARY" >> "$LOGFILE" 2>&1 &
echo $! > "$PIDFILE"
sleep 0.5

if kill -0 "$(cat "$PIDFILE")" 2>/dev/null; then
    echo "Server running (PID $(cat "$PIDFILE")) → http://127.0.0.1:${SERVER_PORT}"
    echo "Log: $LOGFILE"
else
    echo "ERROR: Server failed to start. Check $LOGFILE"
    exit 1
fi
