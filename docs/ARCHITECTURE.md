# Architecture

## Overview

UMIC is a matter-centered intelligence platform. The Matter is the primary organizational unit. Communications, documents, entities, billing, and integrations attach to Matters through explicit relationships and an approval-oriented association engine.

## Clean architecture (backend)

```text
API (FastAPI routers)
        ↓
Application Services
        ↓
Domain / Policy (permissions, AI provider interface, association rules)
        ↓
Repositories
        ↓
PostgreSQL 17 (+ Redis/Celery for async work)
        ↓
External Integrations (Phase 3+)
```

**Rules**

- No business logic in route handlers.
- Authorization enforced in services/dependencies (never UI-only).
- Integrations are interfaces + workers; credentials never hardcoded.
- AI is accessed only through `AIProvider` abstraction.

## Frontend architecture

Feature-oriented Next.js App Router:

```text
src/app/           routes
src/components/    shared UI (layout, shadcn-style primitives)
src/features/      domain feature modules (Phase 2+)
src/hooks/
src/lib/           API client, utils
src/stores/        Zustand (auth session)
src/providers/
src/types/
```

## Runtime topology (Docker Compose)

| Service | Role |
| --- | --- |
| `web` | Next.js UI |
| `api` | FastAPI + Alembic migrate on start |
| `worker` | Celery consumers |
| `postgres` | PostgreSQL 17 with pgvector |
| `redis` | Broker/cache |

## AuthN / AuthZ

- Email/password login (admin-provisioned users).
- bcrypt password hashes.
- JWT access tokens (short-lived) + rotating refresh tokens (hashed at rest).
- Session rows for visibility/revocation.
- RBAC via `roles` → `permissions` → `user_roles`.
- Matter-level authorization hooks reserved for Phase 2 (personal/confidential/privileged flags).

### Roles

| Role | Intent |
| --- | --- |
| System Owner | Full control |
| Billing Administrator | Billing & approvals |
| Matter Administrator | Matters, entities, access |
| Standard User | Day-to-day create/edit on authorized scope |
| Read-Only User | View only |

## Search strategy

**MVP:** PostgreSQL FTS + `pg_trgm` + `pgvector` for future embeddings.

**Later:** OpenSearch (or Elastic) behind a search port so repositories can swap implementations without rewriting domain services.

## AI layer

`app/services/ai/provider.py` defines:

- `associate_matter`
- `summarize`
- `embed`

MVP implementation: `RuleEngineAIProvider` (deterministic, no external calls).
Future: OpenAI / Azure OpenAI providers selected by config.

## Integration architecture (Phase 3)

Workers expose placeholder tasks today:

- `integrations.gmail.sync`
- `integrations.dropbox.sync`
- `integrations.google_drive.sync`
- `documents.extract_text`
- `matters.associate`

Each connection will store OAuth tokens (encrypted), scopes, sync cursors, and status. Source files remain in the provider; UMIC stores metadata, hashes, extracted text, and links.

## Audit

`audit_events` is append-only. Application services write events; no update/delete APIs for normal users.

## Azure alignment

Services map cleanly to:

- Azure Container Apps / App Service
- Azure Database for PostgreSQL
- Azure Cache for Redis
- Azure Blob (optional archive)
- Azure Key Vault (secrets)
- Application Insights (telemetry)
