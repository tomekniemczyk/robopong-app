#!/usr/bin/env bash
# Restart dev servera: stop + start (przekazuje $PORT do obu).
set -e

DIR="$(cd "$(dirname "$0")" && pwd)"
"$DIR/stop.sh"
sleep 1
"$DIR/start.sh"
