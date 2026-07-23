# Implementation Roadmap

## Phase 1 — Foundation (current)

- [x] Monorepo structure
- [x] Docker Compose (web, api, worker, postgres 17+pgvector, redis)
- [x] FastAPI + config + logging + errors
- [x] Auth models, JWT, bcrypt, RBAC
- [x] Alembic migration `001_auth_foundation`
- [x] Seed data
- [x] Celery worker skeleton + placeholder tasks
- [x] AI provider abstraction (rule engine)
- [x] Next.js 15 login + authenticated shell
- [x] Tests + CI skeleton
- [x] Documentation suite

## Phase 2 — Matter & Entity core

- Matter types/statuses/classifications
- Matters CRUD + matter-level ACL (personal/confidential/privileged)
- Entities + aliases + relationships
- Properties, claims, policies, cases, projects
- Audit browse API + Review Queue
- UI: matter/entity list/detail/forms, users/roles screens

## Phase 3 — Integrations & search

- Google OAuth + Gmail / Drive / Docs / Sheets
- Dropbox OAuth
- Idempotent sync workers
- FTS + trigram search APIs
- Integration status UI

## Phase 4 — Billing

- Code libraries, rates
- Proposed billing entries + approval workflow
- Expenses / mileage
- Running totals + Sheets export

## Phase 5 — Intelligence

- Association rule engine production wiring
- OCR (Tesseract) + hash/dedupe
- Embeddings via pluggable AI provider
- Semantic search readiness / OpenSearch adapter design

## Non-goals for Phase 1

No live Gmail/Dropbox/Drive calls, no OCR, no billing generation, no OpenAI calls.
