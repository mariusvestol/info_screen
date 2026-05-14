#!/usr/bin/env bash
set -euo pipefail

cd /home/marves/Desktop/info_screen
shift_status=0
.venv/bin/python shift_sync.py >> shift_sync.log 2>&1 || shift_status=$?

WEB_DIR=/home/marves/Desktop/info_screen_web
if [ -d "$WEB_DIR" ]; then
  npm --prefix "$WEB_DIR" run export:data >> shift_sync.log 2>&1
fi

exit "$shift_status"
