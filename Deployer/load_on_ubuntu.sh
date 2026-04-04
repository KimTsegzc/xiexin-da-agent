#!/usr/bin/env bash
set -euo pipefail

# Usage (as root):
#   bash Deployer/load_on_ubuntu.sh
# Optional overrides:
#   APP_USER=xiexin APP_DIR=/srv/xiexin-da-agent BRANCH=xiexin-vite-proto bash Deployer/load_on_ubuntu.sh

mkdir -p ~/.pip
echo "[global]" > ~/.pip/pip.conf
echo "index-url = https://pypi.tuna.tsinghua.edu.cn/simple" >> ~/.pip/pip.conf
echo "trusted-host = pypi.tuna.tsinghua.edu.cn" >> ~/.pip/pip.conf  # 信任源（避免 HTTPS 证书问题）

APP_USER="${APP_USER:-xiexin}"
APP_DIR="${APP_DIR:-/srv/xiexin-da-agent}"
GIT_URL="${GIT_URL:-https://github.com/KimTsegzc/xiexin-da-agent.git}"
BRANCH="${BRANCH:-xiexin-vite-proto}"
FORCE_BOOTSTRAP="${FORCE_BOOTSTRAP:-0}"
USE_DEADSNAKES="${USE_DEADSNAKES:-}"

log_info() {
  echo "[INFO] $*"
}

log_warn() {
  echo "[WARN] $*"
}

log_error() {
  echo "[ERROR] $*" >&2
}

ensure_repo_owned_by_app_user() {
  if [[ ! -e "$APP_DIR" ]]; then
    return 0
  fi

  local owner
  owner="$(stat -c '%U' "$APP_DIR" 2>/dev/null || echo '')"
  if [[ "$owner" != "$APP_USER" ]]; then
    log_info "Fixing repository ownership for $APP_DIR"
    chown -R "$APP_USER:$APP_USER" "$APP_DIR"
  fi
}

ensure_git_safe_directory() {
  git config --global --get-all safe.directory | grep -Fx "$APP_DIR" >/dev/null 2>&1 || \
    git config --global --add safe.directory "$APP_DIR"

  su - "$APP_USER" -c "git config --global --get-all safe.directory | grep -Fx '$APP_DIR' >/dev/null 2>&1 || git config --global --add safe.directory '$APP_DIR'"
}

resolve_deadsnakes_choice() {
  if [[ "$USE_DEADSNAKES" == "1" || "$USE_DEADSNAKES" == "true" || "$USE_DEADSNAKES" == "Y" || "$USE_DEADSNAKES" == "y" ]]; then
    USE_DEADSNAKES="1"
    return 0
  fi

  if [[ "$USE_DEADSNAKES" == "0" || "$USE_DEADSNAKES" == "false" || "$USE_DEADSNAKES" == "N" || "$USE_DEADSNAKES" == "n" ]]; then
    USE_DEADSNAKES="0"
    return 0
  fi

  if command -v python3.11 >/dev/null 2>&1; then
    USE_DEADSNAKES="0"
    return 0
  fi

  if [[ -t 0 ]]; then
    local answer
    read -r -p "[PROMPT] python3.11 not found. Try deadsnakes PPA now? (Y/N, default N): " answer
    case "$answer" in
      Y|y|yes|YES)
        USE_DEADSNAKES="1"
        ;;
      *)
        USE_DEADSNAKES="0"
        ;;
    esac
  else
    USE_DEADSNAKES="0"
  fi
}

copy_if_changed() {
  local src="$1"
  local dest="$2"
  if [[ ! -f "$dest" ]] || ! cmp -s "$src" "$dest"; then
    cp "$src" "$dest"
    return 0
  fi
  return 1
}

compute_bootstrap_state() {
  (
    cd "$APP_DIR"
    echo "PYTHON_BIN=$PYTHON_BIN"
    "$PYTHON_BIN" --version 2>/dev/null || true
    node --version 2>/dev/null || true
    npm --version 2>/dev/null || true
    sha256sum requirements.txt 2>/dev/null || true
    sha256sum pyproject.toml 2>/dev/null || true
    sha256sum Gateway/Front/react-ui/package.json 2>/dev/null || true
    sha256sum Gateway/Front/react-ui/package-lock.json 2>/dev/null || true
  ) | sha256sum | awk '{print $1}'
}

should_run_bootstrap() {
  local state_file="$1"
  local current_state="$2"

  [[ "$FORCE_BOOTSTRAP" == "1" ]] && return 0
  [[ ! -x "$APP_DIR/.venv311/bin/python" ]] && return 0
  [[ ! -d "$APP_DIR/Gateway/Front/react-ui/node_modules" ]] && return 0
  [[ ! -d "$APP_DIR/Gateway/Front/react-ui/dist" ]] && return 0
  [[ ! -f "$state_file" ]] && return 0

  [[ "$(cat "$state_file" 2>/dev/null || true)" != "$current_state" ]]
}

install_node20() {
  local current_major="$(node -v 2>/dev/null | sed -E 's/^v([0-9]+).*/\1/' || echo 0)"
  if [[ ! "$current_major" =~ ^[0-9]+$ ]]; then
    current_major=0
  fi

  if [[ "$current_major" -ge 20 ]] && command -v npm >/dev/null 2>&1; then
    return 0
  fi

  log_info "Preparing Node.js 20 installation"
  dpkg --configure -a || true
  apt-get -f install -y || true

  if dpkg -s nodejs >/dev/null 2>&1 || dpkg -s npm >/dev/null 2>&1 || dpkg -s libnode-dev >/dev/null 2>&1; then
    log_info "Removing conflicting distro Node packages"
    apt-get remove -y nodejs npm libnode-dev nodejs-doc || true
    apt-get autoremove -y || true
  fi

  curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
  apt-get install -y nodejs
}

if [[ "${EUID}" -ne 0 ]]; then
  log_error "Please run as root."
  exit 1
fi

log_info "APP_USER=$APP_USER"
log_info "APP_DIR=$APP_DIR"
log_info "GIT_URL=$GIT_URL"
log_info "BRANCH=$BRANCH"

echo "[STEP] Install base packages"
apt-get -o Acquire::ForceIPv4=true update
apt-get install -y git curl ca-certificates sudo nginx software-properties-common python3 python3-pip

resolve_deadsnakes_choice

if [[ "$USE_DEADSNAKES" == "1" ]] && ! command -v python3.11 >/dev/null 2>&1; then
  log_info "python3.11 not found, installing via deadsnakes PPA"
  if add-apt-repository -y ppa:deadsnakes/ppa \
      && apt-get -o Acquire::ForceIPv4=true update \
      && apt-get install -y python3.11 python3.11-venv python3.11-dev; then
    log_info "python3.11 installed"
  else
    log_warn "Unable to install python3.11 from deadsnakes, fallback to system python3"
  fi
fi

install_node20

PYTHON_BIN="$(command -v python3.11 || command -v python3 || true)"
NPM_BIN="$(command -v npm || true)"
if [[ -z "$PYTHON_BIN" ]]; then
  log_error "python3 not found after install"
  exit 1
fi
if [[ -z "$NPM_BIN" ]]; then
  log_error "npm not found after install"
  exit 1
fi

log_info "Using Python: $PYTHON_BIN ($($PYTHON_BIN --version))"
log_info "Using Node: $(node --version)"
log_info "Using npm: $(npm --version)"
log_info "USE_DEADSNAKES=$USE_DEADSNAKES"

"$PYTHON_BIN" - <<'PY'
import sys
major, minor = sys.version_info[:2]
if (major, minor) < (3, 10):
  raise SystemExit("Python 3.10+ required")
print("[INFO] Python requirement check passed (>=3.10)")
PY

id -u "$APP_USER" >/dev/null 2>&1 || adduser --disabled-password --gecos "" "$APP_USER"
mkdir -p /srv

# Write pip mirror config for app user (runs as APP_USER so root's ~/.pip/pip.conf is not inherited)
su - "$APP_USER" -c 'mkdir -p ~/.pip && printf "[global]\nindex-url = https://pypi.tuna.tsinghua.edu.cn/simple\ntrusted-host = pypi.tuna.tsinghua.edu.cn\n" > ~/.pip/pip.conf'
log_info "pip mirror configured for $APP_USER"

echo "[STEP] Clone/update repository"
if [[ ! -d "$APP_DIR/.git" ]]; then
  su - "$APP_USER" -c "git clone -b '$BRANCH' '$GIT_URL' '$APP_DIR'"
else
  ensure_repo_owned_by_app_user
  ensure_git_safe_directory
  su - "$APP_USER" -c "cd '$APP_DIR' && git fetch --all && git checkout '$BRANCH' && git pull --ff-only origin '$BRANCH'"
fi

ensure_repo_owned_by_app_user
ensure_git_safe_directory

echo "[STEP] Prepare runtime dir"
mkdir -p "$APP_DIR/.runtime"
chown -R "$APP_USER:$APP_USER" "$APP_DIR/.runtime"

BOOTSTRAP_STATE_FILE="$APP_DIR/.runtime/bootstrap.state"
CURRENT_BOOTSTRAP_STATE="$(compute_bootstrap_state)"

echo "[STEP] Preflight"
su - "$APP_USER" -c "cd '$APP_DIR' && bash Deployer/preflight_ubuntu.sh"

if should_run_bootstrap "$BOOTSTRAP_STATE_FILE" "$CURRENT_BOOTSTRAP_STATE"; then
  echo "[STEP] Bootstrap"
  su - "$APP_USER" -c "cd '$APP_DIR' && PYTHON_BIN=$PYTHON_BIN USE_DEADSNAKES=$USE_DEADSNAKES SKIP_APT=1 bash Deployer/bootstrap_ubuntu.sh"
  CURRENT_BOOTSTRAP_STATE="$(compute_bootstrap_state)"
  printf '%s\n' "$CURRENT_BOOTSTRAP_STATE" > "$BOOTSTRAP_STATE_FILE"
  chown "$APP_USER:$APP_USER" "$BOOTSTRAP_STATE_FILE"
else
  log_info "Bootstrap skipped: dependency state unchanged"
fi

echo "[STEP] Ensure .env"
su - "$APP_USER" -c "cd '$APP_DIR' && [ -f .env ] || cp Deployer/env.production.example .env"
if ! grep -Eq '^(ALIYUN_BAILIAN_API_KEY|DASHSCOPE_API_KEY)=' "$APP_DIR/.env"; then
  log_warn ".env has no API key yet. Edit now: nano $APP_DIR/.env"
fi

echo "[STEP] Install systemd units"
UNITS_CHANGED=0
copy_if_changed "$APP_DIR/Deployer/systemd/xiexin-backend.service" /etc/systemd/system/xiexin-backend.service && UNITS_CHANGED=1 || true
copy_if_changed "$APP_DIR/Deployer/systemd/xiexin-frontend.service" /etc/systemd/system/xiexin-frontend.service && UNITS_CHANGED=1 || true

# Patch ExecStart with actual host paths
PY_PATH="$(readlink -f "$APP_DIR/.venv311/bin/python" || true)"
NPM_PATH="$(command -v npm || true)"

if [[ -n "$PY_PATH" ]]; then
  CURRENT_BACKEND_EXEC="$(grep '^ExecStart=' /etc/systemd/system/xiexin-backend.service || true)"
  EXPECTED_BACKEND_EXEC="ExecStart=${PY_PATH} ${APP_DIR}/orchestrator.py --serve --host 127.0.0.1 --port 8766"
  if [[ "$CURRENT_BACKEND_EXEC" != "$EXPECTED_BACKEND_EXEC" ]]; then
    sed -i "s|^ExecStart=.*orchestrator.py.*|${EXPECTED_BACKEND_EXEC}|" /etc/systemd/system/xiexin-backend.service
    UNITS_CHANGED=1
  fi
else
  log_error "Python executable not found at $APP_DIR/.venv311/bin/python"
  exit 1
fi

if [[ -n "$NPM_PATH" ]]; then
  CURRENT_FRONTEND_EXEC="$(grep '^ExecStart=' /etc/systemd/system/xiexin-frontend.service || true)"
  EXPECTED_FRONTEND_EXEC="ExecStart=${NPM_PATH} run dev -- --host 0.0.0.0 --port 8501"
  if [[ "$CURRENT_FRONTEND_EXEC" != "$EXPECTED_FRONTEND_EXEC" ]]; then
    sed -i "s|^ExecStart=.*npm.*|${EXPECTED_FRONTEND_EXEC}|" /etc/systemd/system/xiexin-frontend.service
    UNITS_CHANGED=1
  fi
else
  log_error "npm executable not found"
  exit 1
fi

if [[ "$UNITS_CHANGED" -eq 1 ]]; then
  systemctl daemon-reload
fi

systemctl enable xiexin-backend xiexin-frontend >/dev/null 2>&1 || true
if systemctl is-active --quiet xiexin-backend; then
  systemctl restart xiexin-backend
else
  systemctl start xiexin-backend
fi

if systemctl is-active --quiet xiexin-frontend; then
  systemctl restart xiexin-frontend
else
  systemctl start xiexin-frontend
fi

echo "[STEP] Configure nginx"
mkdir -p /etc/nginx/sites-available /etc/nginx/sites-enabled
NGINX_CHANGED=0
copy_if_changed "$APP_DIR/Deployer/nginx/xiexin-da-agent.conf" /etc/nginx/sites-available/xiexin-da-agent && NGINX_CHANGED=1 || true
ln -sf /etc/nginx/sites-available/xiexin-da-agent /etc/nginx/sites-enabled/xiexin-da-agent

# Optional: avoid conflicting server_name "_" warning
rm -f /etc/nginx/sites-enabled/default

nginx -t
systemctl enable nginx >/dev/null 2>&1 || true
if systemctl is-active --quiet nginx; then
  if [[ "$NGINX_CHANGED" -eq 1 ]]; then
    systemctl reload nginx
  fi
else
  systemctl start nginx
fi

echo "[STEP] Health check"
su - "$APP_USER" -c "cd '$APP_DIR' && bash Deployer/healthcheck.sh"

echo "[DONE] Services status"
systemctl --no-pager --full status xiexin-backend xiexin-frontend nginx || true

echo
echo "[INFO] Access:"
echo "  - http://<public-ip>/"
echo "  - http://<public-ip>:8765/health"
echo "[INFO] Tencent Cloud security group: allow TCP 80 and TCP 8765"
