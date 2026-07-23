#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

if [[ ! -f .env ]]; then
  cp .env.example .env
  echo "Created .env from .env.example — update secrets before production use."
fi

docker compose up -d --build
echo ""
echo "Services starting. Once healthy:"
echo "  API docs:  http://localhost:8000/docs"
echo "  Web app:   http://localhost:3000"
echo "  Health:    http://localhost:8000/health"
echo ""
echo "Seed data:"
echo "  docker compose exec api python -m app.db.seed"
