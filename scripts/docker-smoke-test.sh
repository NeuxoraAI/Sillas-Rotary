#!/usr/bin/env bash
# Smoke test for the standalone Docker image (Issue #84).
#
# Builds the image, runs it detached, waits for it to come up, and hits
# GET /api/health. If LOGIN_EMAIL/LOGIN_PASSWORD are set, also exercises
# POST /api/auth/login against a real account.
#
# Usage:
#   ./scripts/docker-smoke-test.sh
#   LOGIN_EMAIL=admin@vidaug.mx LOGIN_PASSWORD=changeme123 ./scripts/docker-smoke-test.sh
#
# Requires: docker, curl, and an --env-file at the repo root (.env) with
# DB_*/SUPABASE_*/JWT_SECRET configured — same file used by `start.sh`.
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
IMAGE_TAG="sillas-rotary-api:smoke-test"
CONTAINER_NAME="sillas-rotary-smoke-$$"
PORT="${PORT:-8080}"
ENV_FILE="${ENV_FILE:-$ROOT_DIR/.env}"

if [ ! -f "$ENV_FILE" ]; then
  echo "Error: env file not found at $ENV_FILE (set ENV_FILE=... to override)" >&2
  exit 1
fi

cleanup() {
  docker rm -f "$CONTAINER_NAME" >/dev/null 2>&1 || true
}
trap cleanup EXIT

echo "==> Building image ($IMAGE_TAG)..."
docker build -t "$IMAGE_TAG" "$ROOT_DIR"

echo "==> Starting container on port $PORT..."
docker run -d --rm \
  --name "$CONTAINER_NAME" \
  -p "${PORT}:${PORT}" \
  --env-file "$ENV_FILE" \
  -e "PORT=${PORT}" \
  "$IMAGE_TAG" >/dev/null

echo "==> Waiting for /api/health..."
for _ in $(seq 1 30); do
  if curl -sf "http://localhost:${PORT}/api/health" >/dev/null; then
    break
  fi
  sleep 1
done

health_body="$(curl -sf "http://localhost:${PORT}/api/health")"
echo "GET /api/health -> $health_body"
echo "$health_body" | grep -q '"status":"ok"' || {
  echo "Error: /api/health did not report ok" >&2
  docker logs "$CONTAINER_NAME" >&2 || true
  exit 1
}

if [ -n "${LOGIN_EMAIL:-}" ] && [ -n "${LOGIN_PASSWORD:-}" ]; then
  echo "==> Checking POST /api/auth/login..."
  login_status="$(curl -s -o /dev/null -w '%{http_code}' \
    -X POST "http://localhost:${PORT}/api/auth/login" \
    -H 'Content-Type: application/json' \
    -d "{\"email\":\"${LOGIN_EMAIL}\",\"password\":\"${LOGIN_PASSWORD}\"}")"
  echo "POST /api/auth/login -> HTTP $login_status"
  [ "$login_status" = "200" ] || {
    echo "Error: login smoke check failed (HTTP $login_status)" >&2
    exit 1
  }
else
  echo "==> Skipping login check (set LOGIN_EMAIL/LOGIN_PASSWORD to enable)"
fi

echo "==> Smoke test passed."
