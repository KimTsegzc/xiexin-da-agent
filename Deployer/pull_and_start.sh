#!/usr/bin/env bash
set -euo pipefail

# Thin wrapper around load_on_ubuntu.sh.
# Git clone/pull and service startup are already handled there,
# so this script only forwards the standard deployment env vars.
#
# Usage examples:
#   bash Deployer/pull_and_start.sh
#   BRANCH=main bash Deployer/pull_and_start.sh
#   FORCE_BOOTSTRAP=1 bash Deployer/pull_and_start.sh

APP_USER="${APP_USER:-xiexin}"
APP_DIR="${APP_DIR:-/srv/xiexin-da-agent}"
BRANCH="${BRANCH:-main}"
GIT_URL="${GIT_URL:-https://github.com/KimTsegzc/xiexin-da-agent.git}"
FORCE_BOOTSTRAP="${FORCE_BOOTSTRAP:-0}"
USE_DEADSNAKES="${USE_DEADSNAKES:-}"

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"

if [[ "${EUID}" -ne 0 ]]; then
  echo "[INFO] Re-running with sudo..."
  exec sudo -E \
    APP_USER="$APP_USER" \
    APP_DIR="$APP_DIR" \
    BRANCH="$BRANCH" \
    GIT_URL="$GIT_URL" \
    FORCE_BOOTSTRAP="$FORCE_BOOTSTRAP" \
    USE_DEADSNAKES="$USE_DEADSNAKES" \
    bash "$0" "$@"
fi

APP_USER="$APP_USER" \
APP_DIR="$APP_DIR" \
BRANCH="$BRANCH" \
GIT_URL="$GIT_URL" \
FORCE_BOOTSTRAP="$FORCE_BOOTSTRAP" \
USE_DEADSNAKES="$USE_DEADSNAKES" \
bash "$SCRIPT_DIR/load_on_ubuntu.sh"