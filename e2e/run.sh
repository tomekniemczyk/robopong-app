#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"

if [ ! -d venv ]; then
  echo "venv/ not found — run ./setup.sh first"
  exit 1
fi

PORT="${E2E_PORT:-8766}"
REPO_ROOT="$(cd .. && pwd)"
BACKEND_VENV="$REPO_ROOT/backend/venv"

if [ ! -f "$BACKEND_VENV/bin/uvicorn" ]; then
  echo "Backend venv not found at $BACKEND_VENV — run backend setup first"
  exit 1
fi

echo "→ Booting backend (simulation) on :$PORT"
cd "$REPO_ROOT/backend"
SIMULATION=1 "$BACKEND_VENV/bin/uvicorn" main:app --host 127.0.0.1 --port "$PORT" > /tmp/robopong_e2e_server.log 2>&1 &
SERVER_PID=$!
trap "kill $SERVER_PID 2>/dev/null || true" EXIT

for i in $(seq 1 20); do
  if curl -sf "http://127.0.0.1:$PORT/api/serves/tree" > /dev/null 2>&1; then
    break
  fi
  sleep 0.5
done

echo "→ Running e2e suite"
cd "$REPO_ROOT/e2e"
E2E_BASE_URL="http://127.0.0.1:$PORT" venv/bin/pytest -v "$@"
