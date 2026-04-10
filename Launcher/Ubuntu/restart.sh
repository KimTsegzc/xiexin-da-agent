#!/usr/bin/env bash
# XIEXin DA Agent — Ubuntu restart script (systemd)
# Usage:
#   ./Launcher/Ubuntu/restart.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

phase() { echo "[ubuntu-restart] $*"; }

phase "stopping"
bash "$SCRIPT_DIR/stop.sh"
phase "starting"
bash "$SCRIPT_DIR/start.sh"
