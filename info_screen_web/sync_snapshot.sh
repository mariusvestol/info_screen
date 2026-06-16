#!/usr/bin/env bash
set -euo pipefail

cd /home/marves/Desktop/info_screen/info_screen_web
node scripts/export-data.mjs >> data_sync.log 2>&1
