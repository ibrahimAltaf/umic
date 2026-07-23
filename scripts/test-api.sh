#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR/apps/api"

export SECRET_KEY="${SECRET_KEY:-test-secret-key-must-be-at-least-32-characters-long-xx}"
export JWT_SECRET_KEY="${JWT_SECRET_KEY:-test-jwt-secret-key-must-be-at-least-32-characters-xx}"
export DATABASE_URL="${DATABASE_URL:-sqlite+pysqlite:///:memory:}"
export APP_ENV=test
export DEBUG=true

python -m pytest "$@"
