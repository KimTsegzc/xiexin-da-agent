#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
FRONTEND_DIR="$ROOT_DIR/Gateway/Front/react-ui"

pass() { printf '[PASS] %s\n' "$1"; }
warn() { printf '[WARN] %s\n' "$1"; }
fail() { printf '[FAIL] %s\n' "$1"; exit 1; }
check_cmd() {
  local name="$1"
  command -v "$name" >/dev/null 2>&1 || fail "Missing command: $name"
  pass "Command found: $name"
}

printf 'Project root: %s\n' "$ROOT_DIR"

if [[ "$(uname -s)" != "Linux" ]]; then
  fail "This script is intended for Ubuntu/Linux."
fi
pass "Linux runtime detected"

if [[ -r /etc/os-release ]]; then
  . /etc/os-release
  printf 'OS: %s %s\n' "${NAME:-Unknown}" "${VERSION_ID:-}" 
  if [[ "${ID:-}" != "ubuntu" ]]; then
    warn "Non-Ubuntu Linux detected; scripts may still work but are tuned for Ubuntu."
  else
    pass "Ubuntu detected"
  fi
fi

for path in \
  "$ROOT_DIR/orchestrator.py" \
  "$ROOT_DIR/pyproject.toml" \
  "$ROOT_DIR/Gateway/Back/llm_provider.py" \
  "$FRONTEND_DIR/package.json"
 do
  [[ -f "$path" ]] || fail "Required file missing: $path"
  pass "Found required file: $path"
done

check_cmd python3
check_cmd npm
check_cmd node
check_cmd curl

python3 - <<'PY'
import sys
major, minor = sys.version_info[:2]
if (major, minor) < (3, 10):
  raise SystemExit('Python 3.10+ required')
print('[PASS] Python version is', sys.version.split()[0])
PY

node -e "const [major]=process.versions.node.split('.').map(Number); if (major < 20) process.exit(1); console.log('[PASS] Node version is', process.versions.node);" || fail "Node.js 20+ required"
npm -v | awk '{print "[PASS] npm version is "$0}'

if [[ -f "$ROOT_DIR/.env" ]]; then
  pass "Found .env"
  if grep -Eq '^(ALIYUN_BAILIAN_API_KEY|DASHSCOPE_API_KEY)=' "$ROOT_DIR/.env"; then
    pass ".env contains an API key entry"
  else
    warn ".env exists but no ALIYUN_BAILIAN_API_KEY/DASHSCOPE_API_KEY entry was found"
  fi
else
  warn "No .env found at project root"
fi

if [[ -f "$FRONTEND_DIR/package-lock.json" ]]; then
  pass "Found package-lock.json"
else
  warn "package-lock.json missing; npm install will be used instead of npm ci"
fi

for port in 8501 8766; do
  if ss -ltn "( sport = :$port )" 2>/dev/null | tail -n +2 | grep -q ":$port"; then
    warn "Port $port is already in use"
  else
    pass "Port $port is currently free"
  fi
done

printf '\nPreflight checks completed.\n'
