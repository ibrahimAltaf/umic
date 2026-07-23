# Unified Matter Intelligence Center (UMIC)

Enterprise matter-centered platform for communications, documents, entities, billing, and audit — with Gmail, Google Drive, and Dropbox integration architecture.

> **Current status:** Phase 1 foundation (monorepo, Docker, auth/RBAC, base UI). Integrations and domain CRUD land in later phases.

## Stack

| Layer | Technology |
| --- | --- |
| Frontend | Next.js 15, React 19, TypeScript, Tailwind, TanStack Query, RHF, Zod, Zustand |
| Backend | Python 3.13, FastAPI, SQLAlchemy 2, Alembic, Pydantic v2 |
| Database | PostgreSQL 17 + pgvector, pg_trgm, full-text |
| Workers | Redis + Celery |
| Auth | JWT access/refresh, bcrypt, RBAC |
| Deploy target | Microsoft Azure (see `DEPLOYMENT_GUIDE.md`) |

## Quick start (Docker)

```bash
cp .env.example .env
chmod +x scripts/*.sh
./scripts/dev-up.sh
./scripts/seed.sh
```

| Service | URL |
| --- | --- |
| Web | http://localhost:3000 |
| API | http://localhost:8000 |
| OpenAPI docs | http://localhost:8000/docs |
| Health | http://localhost:8000/health |

### Seeded admin (development only)

| Field | Value |
| --- | --- |
| Email | `admin@example.com` (or `SEED_ADMIN_EMAIL`) |
| Password | `ChangeMeAdmin123!` (or `SEED_ADMIN_PASSWORD`) |

Additional sample users: `billing.admin@example.com`, `matter.admin@example.com`, `standard.user@example.com`, `readonly.user@example.com` (passwords in seed output / `app/db/seed.py`).

## Local development (without full Compose)

### Prerequisites

- Docker Desktop
- Node.js 20+
- Python 3.13+
- PostgreSQL 17 (or Compose `postgres` + `redis` only)

### API

```bash
cd apps/api
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
# point DATABASE_URL / REDIS at local or Compose services
alembic upgrade head
python -m app.db.seed
uvicorn app.main:app --reload --port 8000
```

### Web

```bash
cd apps/web
npm install
npm run dev
```

### Worker

```bash
cd apps/worker
pip install -r requirements.txt
celery -A app.celery_app.celery worker --loglevel=INFO
```

## Tests

```bash
./scripts/test-api.sh
cd apps/web && npm install && npm test
```

## Monorepo layout

```text
apps/web          Next.js frontend
apps/api          FastAPI backend
apps/worker       Celery workers
packages/         Shared packages (reserved)
infrastructure/   Docker & deployment
docs/             Additional docs (mirrors root guides)
scripts/          Dev helpers
```

## Documentation

| File | Purpose |
| --- | --- |
| [ARCHITECTURE.md](./ARCHITECTURE.md) | System design |
| [DATABASE_SCHEMA.md](./DATABASE_SCHEMA.md) | Schema (Phase 1 + planned) |
| [API_DOCUMENTATION.md](./API_DOCUMENTATION.md) | API reference |
| [ENVIRONMENT_SETUP.md](./ENVIRONMENT_SETUP.md) | Env vars & local setup |
| [SECURITY_GUIDELINES.md](./SECURITY_GUIDELINES.md) | Security rules |
| [DEPLOYMENT_GUIDE.md](./DEPLOYMENT_GUIDE.md) | Azure deployment |
| [IMPLEMENTATION_ROADMAP.md](./IMPLEMENTATION_ROADMAP.md) | Phased delivery |
| [DEVELOPMENT_PROGRESS.md](./DEVELOPMENT_PROGRESS.md) | Live progress |

## Core principles

1. **Matter-centered** — every record relates to one or more Matters.
2. **One record, many relationships** — no unnecessary duplication.
3. **Preserve sources** — index metadata/links; never alter Gmail/Drive/Dropbox originals.
4. **Automation proposes, user approves** — no silent finalization of uncertain work.
5. **Append-only audit** — sensitive actions are ledgered.

## License

Proprietary — all rights reserved.
