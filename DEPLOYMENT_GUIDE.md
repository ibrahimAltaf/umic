# Deployment Guide (Microsoft Azure)

## Target topology

| Component | Azure service |
| --- | --- |
| Web + API + Worker containers | Azure Container Apps (preferred) or App Service |
| PostgreSQL 17 + pgvector | Azure Database for PostgreSQL Flexible Server |
| Redis | Azure Cache for Redis |
| Secrets | Azure Key Vault |
| Images | Azure Container Registry |
| Optional file archive | Azure Blob Storage |
| Telemetry | Application Insights |

## Build & push

```bash
az acr login --name <registry>
docker build -f infrastructure/docker/api/Dockerfile -t <registry>.azurecr.io/umic-api:0.1.0 .
docker build -f infrastructure/docker/web/Dockerfile -t <registry>.azurecr.io/umic-web:0.1.0 .
docker build -f infrastructure/docker/worker/Dockerfile -t <registry>.azurecr.io/umic-worker:0.1.0 .
docker push <registry>.azurecr.io/umic-api:0.1.0
docker push <registry>.azurecr.io/umic-web:0.1.0
docker push <registry>.azurecr.io/umic-worker:0.1.0
```

## Configuration

Bind Container App secrets from Key Vault:

- `DATABASE_URL` (TLS)
- `JWT_SECRET_KEY`, `SECRET_KEY`
- `REDIS_URL`, Celery URLs
- OAuth client secrets (Phase 3)

Set `APP_ENV=production`, `DEBUG=false`.

## Migrations

Run as a job / init container before traffic:

```bash
alembic upgrade head
python -m app.db.seed   # only for non-prod bootstrap
```

Compose already runs `alembic upgrade head` on API start for development.

## Networking

- Private VNet integration for Postgres/Redis when possible.
- Public ingress only for web + API.
- Restrict CORS to production web origins.

## Health probes

- API: `GET /health`
- Worker: Celery inspect / custom heartbeat task `worker.health.ping`

## CI/CD

GitHub Actions workflow `.github/workflows/ci.yml` runs API pytest + web build/test.
Extend with deploy jobs using OIDC to Azure (federated credentials).

## Notes

Infrastructure-as-code templates under `infrastructure/deployment/` will be added when Azure subscription details are available.
