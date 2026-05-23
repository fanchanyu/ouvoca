#!/usr/bin/env bash
# Stop Ouvoca services started by start.sh
cd "$(dirname "$0")"

for name in backend frontend; do
    if [ -f ".${name}.pid" ]; then
        PID=$(cat ".${name}.pid")
        if kill -0 "$PID" 2>/dev/null; then
            kill "$PID" 2>/dev/null && echo "  Stopped $name (PID $PID)"
        fi
        rm ".${name}.pid"
    fi
done

# Also kill anything on :8000 / :5173
for port in 8000 5173; do
    PID=$(lsof -t -i:"$port" 2>/dev/null || true)
    if [ -n "$PID" ]; then
        kill -9 "$PID" 2>/dev/null && echo "  Killed leftover process on :$port (PID $PID)"
    fi
done

echo "  All services stopped."
