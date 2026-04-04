#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_DIR="$ROOT_DIR/.venv311"
FRONTEND_DIR="$ROOT_DIR/Gateway/Front/react-ui"
PYTHON_BIN="${PYTHON_BIN:-python3}"
USE_DEADSNAKES="${USE_DEADSNAKES:-0}"
SKIP_APT="${SKIP_APT:-0}"

install_node20() {
  local current_major="$(node -v 2>/dev/null | sed -E 's/^v([0-9]+).*/\1/' || echo 0)"
  if [[ ! "$current_major" =~ ^[0-9]+$ ]]; then
    current_major=0
  fi

  if [[ "$current_major" -ge 20 ]] && command -v npm >/dev/null 2>&1; then
    return 0
  fi

  echo "[INFO] Preparing Node.js 20 installation"
  sudo dpkg --configure -a || true
  sudo apt-get -f install -y || true

  if dpkg -s nodejs >/dev/null 2>&1 || dpkg -s npm >/dev/null 2>&1 || dpkg -s libnode-dev >/dev/null 2>&1; then
    echo "[INFO] Removing conflicting distro Node packages"
    sudo apt-get remove -y nodejs npm libnode-dev nodejs-doc || true
    sudo apt-get autoremove -y || true
  fi

  curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
  sudo apt-get install -y nodejs
}

need_cmd() {
  command -v "$1" >/dev/null 2>&1 || {
    echo "[ERROR] Missing command: $1" >&2
    exit 1
  }
}

need_cmd "$PYTHON_BIN"
need_cmd curl

if [[ "$SKIP_APT" != "1" ]]; then
  need_cmd sudo
fi

echo "[INFO] Root dir: $ROOT_DIR"

if [[ "$SKIP_APT" == "1" ]]; then
  echo "[INFO] SKIP_APT=1, skipping apt package installation"
else
  echo "[INFO] Installing Ubuntu packages"
  sudo apt-get -o Acquire::ForceIPv4=true update
  sudo apt-get install -y \
    git \
    curl \
    ca-certificates \
    software-properties-common \
    build-essential \
    python3 \
    python3-venv \
    python3-pip \
    nginx
fi

if [[ "$SKIP_APT" != "1" ]] && [[ "$USE_DEADSNAKES" == "1" ]] && ! command -v python3.11 >/dev/null 2>&1; then
  echo "[INFO] Installing Python 3.11 via deadsnakes PPA"
  if sudo add-apt-repository -y ppa:deadsnakes/ppa \
      && sudo apt-get -o Acquire::ForceIPv4=true update \
      && sudo apt-get install -y python3.11 python3.11-venv python3.11-dev; then
    echo "[INFO] Python 3.11 installed"
  else
    echo "[WARN] Unable to install python3.11 from deadsnakes, will fallback to system python3"
  fi
fi

PYTHON_BIN="$(command -v python3.11 || command -v python3 || true)"
if [[ -z "$PYTHON_BIN" ]]; then
  echo "[ERROR] python3 is required but not available." >&2
  exit 1
fi

if [[ "$SKIP_APT" == "1" ]]; then
  echo "[INFO] SKIP_APT=1, skipping Node.js installation"
else
  install_node20
fi

echo "[INFO] Python version: $($PYTHON_BIN --version)"
echo "[INFO] Node version: $(node --version)"
echo "[INFO] npm version: $(npm --version)"

"$PYTHON_BIN" - <<'PY'
import sys
major, minor = sys.version_info[:2]
if (major, minor) < (3, 10):
  raise SystemExit("Python 3.10+ required")
print("[INFO] Python requirement check passed (>=3.10)")
PY

if [[ ! -d "$VENV_DIR" ]]; then
  echo "[INFO] Creating virtual environment at $VENV_DIR"
  "$PYTHON_BIN" -m venv "$VENV_DIR"
fi

source "$VENV_DIR/bin/activate"
python -m pip install --upgrade pip wheel setuptools

if [[ -f "$ROOT_DIR/pyproject.toml" ]]; then
  echo "[INFO] Installing project package from pyproject.toml (single source of truth)"
  pip install -e "$ROOT_DIR"
elif [[ -f "$ROOT_DIR/requirements.txt" ]]; then
  echo "[INFO] pyproject.toml not found, falling back to requirements.txt"
  pip install -r "$ROOT_DIR/requirements.txt"
fi

if python -m pip show streamlit >/dev/null 2>&1; then
  echo "[INFO] Removing legacy Streamlit package"
  pip uninstall -y streamlit >/dev/null 2>&1 || true
fi

echo "[INFO] Configuring npm registry mirror"
npm config set registry https://registry.npmmirror.com

if [[ -f "$FRONTEND_DIR/package-lock.json" ]]; then
  echo "[INFO] Installing frontend dependencies with npm ci"
  npm --prefix "$FRONTEND_DIR" ci
else
  echo "[INFO] Installing frontend dependencies with npm install"
  npm --prefix "$FRONTEND_DIR" install
fi

echo "[INFO] Building frontend assets"
npm --prefix "$FRONTEND_DIR" run build

if [[ ! -f "$ROOT_DIR/.env" ]]; then
  echo "[WARN] .env not found. Creating from template."
  cp "$ROOT_DIR/Deployer/env.production.example" "$ROOT_DIR/.env"
  echo "[WARN] Edit $ROOT_DIR/.env before starting services."
fi

echo "[INFO] Bootstrap complete"
echo "[INFO] Next steps:"
echo "       1. edit $ROOT_DIR/.env"
echo "       2. copy systemd templates from Deployer/systemd/"
echo "       3. copy nginx config from Deployer/nginx/"
