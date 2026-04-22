#!/usr/bin/env bash
# Dev server starter — background z PID file, logi do pliku.
# Port konfigurowalny przez $PORT (domyślnie 8000).
set -e

APP_DIR="$(cd "$(dirname "$0")" && pwd)"
BACKEND="$APP_DIR/backend"
PORT="${PORT:-8000}"
PIDFILE="/tmp/robopong-dev.pid"
LOGFILE="$BACKEND/uvicorn-dev.log"

cd "$BACKEND"

if [ ! -d venv ]; then
  python3 -m venv venv
  venv/bin/pip install -r requirements.txt
fi

if [ -f "$PIDFILE" ] && kill -0 "$(cat "$PIDFILE")" 2>/dev/null; then
  echo "Serwer dev już działa (PID $(cat "$PIDFILE"), port $PORT)"
  echo "Aby zrestartować: ./restart.sh    Aby zatrzymać: ./stop.sh"
  exit 0
fi
rm -f "$PIDFILE"

pkill -f "uvicorn main:app.*--port $PORT" 2>/dev/null && sleep 1 || true

if ss -tln 2>/dev/null | awk '{print $4}' | grep -qE ":$PORT\$"; then
  owner=$(ss -tlnp 2>/dev/null | awk -v p=":$PORT" '$4 ~ p {print $NF}' | head -1)
  echo "BŁĄD: Port $PORT jest zajęty przez inny proces: $owner"
  echo "Ustaw inny port: PORT=8002 ./start.sh"
  exit 1
fi

nohup venv/bin/uvicorn main:app --host 0.0.0.0 --port "$PORT" \
  </dev/null >"$LOGFILE" 2>&1 &

echo $! > "$PIDFILE"
echo "Serwer dev uruchomiony (PID $!, port $PORT)"
echo "Logi: $LOGFILE"
