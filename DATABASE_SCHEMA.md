# Database Schema

## Extensions (enabled on init)

- `uuid-ossp`, `pgcrypto`
- `pg_trgm`, `unaccent` (search)
- `vector` (pgvector — embeddings later)

## Phase 1 tables (migrated)

### Authentication & RBAC

| Table | Purpose |
| --- | --- |
| `users` | Accounts (UUID PK, soft delete, lockout fields) |
| `roles` | System roles |
| `permissions` | Fine-grained permission codes |
| `role_permissions` | M2M role ↔ permission |
| `user_roles` | M2M user ↔ role |
| `refresh_tokens` | Hashed refresh tokens + revoke metadata |
| `user_sessions` | Session tracking |
| `password_reset_tokens` | Reset structure (email delivery later) |

### Audit

| Table | Purpose |
| --- | --- |
| `audit_events` | Append-only ledger (JSONB previous/new values) |

Migration: `apps/api/alembic/versions/001_auth_foundation.py`

## Planned Phase 2+ (not yet migrated)

### Matter domain

`matters`, `matter_types`, `matter_statuses`, `matter_aliases`, `billing_classifications`

### Entities

`entities`, `entity_types`, `entity_aliases`, `entity_contacts`, `entity_addresses`, `matter_entity_relationships`

### Domain records

`properties`, `addresses`, `claims`, `policies`, `cases`, `appraisals`, `projects`

### Communications / documents

`emails`, `email_participants`, `email_attachments`, `email_headers`, `email_threads`, `documents`, `document_versions`, `document_text_extractions`, `document_hashes`, `source_links`

### Associations / workflow

`matter_associations`, `entity_associations`, `association_evidence`, `review_queue_items`, `discrepancy_alerts`

### Billing

`billing_codes`, `billing_code_libraries`, `billing_rates`, `billing_entries`, `expenses`, `mileage_entries`, `invoices`, `invoice_items`, `payments`

### Integrations / jobs

`integration_connections`, `synchronization_jobs`, `failed_jobs`, `error_logs`

## Conventions

- UUID primary keys for business records
- `created_at` / `updated_at` timestamps (timestamptz)
- Soft delete where recoverable (`is_deleted`, `deleted_at`)
- Monetary values: `NUMERIC` (never float) — when billing tables land
- Immutable audit rows
- Indexes on foreign keys, status, and search columns
