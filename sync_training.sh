#!/usr/bin/env bash
set -euo pipefail

cd /home/marves/Desktop/info_screen
training_status=0
node sync_training.mjs >> training_sync.log 2>&1 || training_status=$?

WEB_DIR=/home/marves/Desktop/info_screen/info_screen_web
if [ -d "$WEB_DIR" ]; then
  npm --prefix "$WEB_DIR" run export:data >> training_sync.log 2>&1
fi

exit "$training_status"
