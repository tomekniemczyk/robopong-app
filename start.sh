#!/usr/bin/env bash
set -e
cd "$(dirname "$0")/backend"

if [ ! -d venv ]; then
  python3 -m venv venv
  venv/bin/pip install -r requirements.txt
fi

exec venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000
