#!/usr/bin/env bash
# XIEXin DA Agent — Ubuntu start script (systemd)
# Usage:
#   ./Launcher/Ubuntu/start.sh

set -euo pipefail

APP_DIR="${APP_DIR:-/srv/xiexin-da-agent}"
BACKEND_SERVICE="${BACKEND_SERVICE:-xiexin-backend}"
FRONTEND_SERVICE="${FRONTEND_SERVICE:-xiexin-frontend}"

phase() { echo "[ubuntu-start] $*"; }

phase "app_dir=$APP_DIR"
if [[ ! -f "$APP_DIR/.env" ]]; then
  echo "[ubuntu-start] ERROR: missing $APP_DIR/.env" >&2
  exit 1
fi

sudo systemctl daemon-reload
sudo systemctl enable "$BACKEND_SERVICE" "$FRONTEND_SERVICE" >/dev/null 2>&1 || true
sudo systemctl start "$BACKEND_SERVICE" "$FRONTEND_SERVICE"

backend_status="$(systemctl is-active "$BACKEND_SERVICE" || true)"
frontend_status="$(systemctl is-active "$FRONTEND_SERVICE" || true)"
phase "backend=$backend_status frontend=$frontend_status"

if [[ "$backend_status" != "active" || "$frontend_status" != "active" ]]; then
  echo "[ubuntu-start] ERROR: service not active" >&2
  sudo systemctl status "$BACKEND_SERVICE" --no-pager -l || true
  sudo systemctl status "$FRONTEND_SERVICE" --no-pager -l || true
  exit 1
fi

phase "done"
