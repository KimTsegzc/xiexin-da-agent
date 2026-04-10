#!/usr/bin/env bash
# XIEXin DA Agent — Ubuntu stop script (systemd)
# Usage:
#   ./Launcher/Ubuntu/stop.sh

set -euo pipefail

BACKEND_SERVICE="${BACKEND_SERVICE:-xiexin-backend}"
FRONTEND_SERVICE="${FRONTEND_SERVICE:-xiexin-frontend}"

phase() { echo "[ubuntu-stop] $*"; }

sudo systemctl stop "$BACKEND_SERVICE" "$FRONTEND_SERVICE" || true
backend_status="$(systemctl is-active "$BACKEND_SERVICE" || true)"
frontend_status="$(systemctl is-active "$FRONTEND_SERVICE" || true)"
phase "backend=$backend_status frontend=$frontend_status"
phase "done"
