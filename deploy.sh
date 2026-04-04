#!/usr/bin/env bash
# Auto-deploy: co 15s sprawdza git, deploy tylko jeśli CI (GitHub Actions) przeszło
set -euo pipefail

APP_DIR="$(cd "$(dirname "$0")" && pwd)"
BACKEND="$APP_DIR/backend"
PORT=8001
LOCKFILE="/tmp/robopong-deploy.lock"
LOGFILE="/tmp/robopong-deploy.log"
DEPLOYED_SHA_FILE="/tmp/robopong-deployed-sha"

log() { echo "[$(date '+%H:%M:%S')] $*" >> "$LOGFILE"; }

if [ -f "$LOCKFILE" ] && kill -0 "$(cat "$LOCKFILE")" 2>/dev/null; then
    echo "Deploy już działa (PID $(cat "$LOCKFILE"))"
    exit 0
fi
echo $$ > "$LOCKFILE"
trap 'rm -f "$LOCKFILE"' EXIT

restart_server() {
    log "Restart serwera na porcie $PORT"
    pkill -f "uvicorn main:app.*$PORT" 2>/dev/null || true
    sleep 2
    cd "$BACKEND"
    [ -d venv ] || python3 -m venv venv
    venv/bin/pip install -q -r requirements.txt 2>/dev/null
    nohup venv/bin/uvicorn main:app --host 0.0.0.0 --port "$PORT" \
        </dev/null >"$BACKEND/uvicorn.log" 2>&1 &
    log "Serwer uruchomiony (PID $!)"
}

ci_passed() {
    local sha="$1"
    local status
    status=$(gh run list \
        --repo tomekniemczyk/robopong-app \
        --branch main \
        --commit "$sha" \
        --status completed \
        --json conclusion \
        --jq '.[0].conclusion' 2>/dev/null) || true

    if [ "$status" = "success" ]; then
        return 0
    elif [ -z "$status" ]; then
        log "CI dla $sha: w toku lub brak workflow"
        return 1
    else
        log "CI dla $sha: $status (FAILED)"
        return 1
    fi
}

pgrep -f "uvicorn main:app.*$PORT" >/dev/null 2>&1 || restart_server

# Initialize deployed SHA with current running version
CURRENT_HEAD=$(cd "$APP_DIR" && git rev-parse HEAD)
[ -f "$DEPLOYED_SHA_FILE" ] || echo "$CURRENT_HEAD" > "$DEPLOYED_SHA_FILE"

log "Auto-deploy start (co 15s, wymaga CI pass)"

while true; do
    cd "$APP_DIR"
    git fetch origin main 2>>"$LOGFILE" || { sleep 15; continue; }

    REMOTE_HEAD=$(git rev-parse origin/main)
    LOCAL_HEAD=$(git rev-parse HEAD)
    DEPLOYED_SHA=$(cat "$DEPLOYED_SHA_FILE" 2>/dev/null || echo "")

    # Pull remote changes if any
    if [ "$LOCAL_HEAD" != "$REMOTE_HEAD" ]; then
        if ci_passed "$REMOTE_HEAD"; then
            log "Pulling remote changes: $REMOTE_HEAD"
            git pull --ff-only origin main 2>>"$LOGFILE" || { sleep 15; continue; }
            LOCAL_HEAD=$(git rev-parse HEAD)
        else
            sleep 15; continue
        fi
    fi

    # Deploy if HEAD differs from last deployed version
    if [ "$LOCAL_HEAD" != "$DEPLOYED_SHA" ]; then
        if ci_passed "$LOCAL_HEAD"; then
            log "CI PASSED — deploying $LOCAL_HEAD"
            restart_server
            echo "$LOCAL_HEAD" > "$DEPLOYED_SHA_FILE"
        fi
    fi

    sleep 15
done
