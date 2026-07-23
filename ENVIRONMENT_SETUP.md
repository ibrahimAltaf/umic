# Environment Setup

## 1. Copy template

```bash
cp .env.example .env
```

Never commit `.env`.

## 2. Required variables

| Variable | Description |
| --- | --- |
| `SECRET_KEY` | App secret (≥32 chars) |
| `JWT_SECRET_KEY` | JWT signing secret (≥32 chars) |
| `DATABASE_URL` | SQLAlchemy URL (`postgresql+psycopg://...`) |
| `REDIS_URL` | Redis connection |
| `CELERY_BROKER_URL` | Celery broker |
| `CELERY_RESULT_BACKEND` | Celery results |
| `CORS_ORIGINS` | Comma-separated origins (include `http://localhost:3000`) |
| `NEXT_PUBLIC_API_URL` | Browser-facing API base URL |
| `SEED_ADMIN_EMAIL` / `SEED_ADMIN_PASSWORD` | Bootstrap admin |

## 3. Docker development

```bash
./scripts/dev-up.sh
./scripts/seed.sh
```

Compose wires:

- Postgres 17 + pgvector (`pgvector/pgvector:pg17`)
- Redis 7
- API (migrate on start)
- Worker
- Web

## 4. Host-mode overrides

When API runs on the host against Compose Postgres/Redis:

```bash
DATABASE_URL=postgresql+psycopg://umic:umic_dev_password_change_me@localhost:5432/umic
REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=redis://localhost:6379/1
CELERY_RESULT_BACKEND=redis://localhost:6379/2
```

## 5. OAuth placeholders (Phase 3/6)

`GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `DROPBOX_APP_KEY`, `DROPBOX_APP_SECRET` — leave empty until integrations begin.

## 6. Production checklist

- Rotate all secrets via Azure Key Vault
- `APP_ENV=production`, `DEBUG=false`
- Restrict `CORS_ORIGINS`
- Disable public docs if required by policy
- Use managed Postgres TLS connection strings
- Separate Redis databases/instances for cache vs broker
