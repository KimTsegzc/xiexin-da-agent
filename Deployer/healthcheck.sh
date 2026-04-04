#!/usr/bin/env bash
set -euo pipefail

FRONTEND_URL="${FRONTEND_URL:-http://127.0.0.1:8501}"
# Backend binds to 127.0.0.1:8766 (internal). Check it directly to avoid nginx dependency.
BACKEND_HEALTH_URL="${BACKEND_HEALTH_URL:-http://127.0.0.1:8766/health}"
BACKEND_CONFIG_URL="${BACKEND_CONFIG_URL:-http://127.0.0.1:8766/api/frontend-config}"
CHECK_RETRIES="${CHECK_RETRIES:-30}"
CHECK_INTERVAL_SECONDS="${CHECK_INTERVAL_SECONDS:-2}"

check_url() {
  local label="$1"
  local url="$2"
  local attempt=1
  echo "[INFO] Checking $label -> $url"
  while [[ "$attempt" -le "$CHECK_RETRIES" ]]; do
    if curl -fsS "$url" >/tmp/xiexin_healthcheck.$$; then
      echo "[PASS] $label OK (attempt $attempt/$CHECK_RETRIES)"
      rm -f /tmp/xiexin_healthcheck.$$
      return 0
    fi
    sleep "$CHECK_INTERVAL_SECONDS"
    attempt=$((attempt + 1))
  done

  echo "[FAIL] $label failed after $CHECK_RETRIES attempts: $url"
  rm -f /tmp/xiexin_healthcheck.$$
  exit 1
}

check_url "frontend" "$FRONTEND_URL"
check_url "backend health" "$BACKEND_HEALTH_URL"
check_url "frontend config" "$BACKEND_CONFIG_URL"

echo "[PASS] All health checks passed"
