#!/usr/bin/env bash
# Zatrzymuje dev server uruchomiony przez start.sh.
set -e

PORT="${PORT:-8000}"
PIDFILE="/tmp/robopong-dev.pid"

stopped=0

if [ -f "$PIDFILE" ]; then
  pid=$(cat "$PIDFILE")
  if kill -0 "$pid" 2>/dev/null; then
    kill "$pid" 2>/dev/null || true
    for _ in 1 2 3 4 5; do
      kill -0 "$pid" 2>/dev/null || break
      sleep 1
    done
    kill -0 "$pid" 2>/dev/null && kill -9 "$pid" 2>/dev/null || true
    echo "Zatrzymano PID $pid"
    stopped=1
  fi
  rm -f "$PIDFILE"
fi

# Fallback: ubij sierotę jeśli została (start bez PID file, stary proces)
if pkill -f "uvicorn main:app.*--port $PORT" 2>/dev/null; then
  echo "Zatrzymano sierotę uvicorn na porcie $PORT"
  stopped=1
fi

if [ "$stopped" -eq 0 ]; then
  echo "Serwer dev nie działa"
fi
