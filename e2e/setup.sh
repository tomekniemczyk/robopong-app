#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"

if [ ! -d venv ]; then
  python3 -m venv venv
fi
venv/bin/pip install -q --upgrade pip
venv/bin/pip install -q -r requirements.txt
venv/bin/playwright install chromium
echo "E2E setup complete. Run: ./run.sh"
