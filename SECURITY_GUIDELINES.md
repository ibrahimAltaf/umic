# Security Guidelines

## Secrets

- Never commit secrets, tokens, or `.env` files.
- Use Azure Key Vault (or equivalent) in production.
- Rotate `SECRET_KEY` / `JWT_SECRET_KEY` if leaked.

## Authentication

- Passwords hashed with **bcrypt** via Passlib.
- Access tokens are short-lived JWTs.
- Refresh tokens are opaque JWTs with `jti`, stored as SHA-256 hashes, rotated on refresh, and revocable.
- Disabled / soft-deleted users cannot authenticate.
- Failed login lockout after repeated failures.

## Authorization

- RBAC enforced in FastAPI dependencies and services.
- Frontend hiding is convenience only — never the security boundary.
- Matter-level personal/confidential/privileged checks will extend `require_permissions` in Phase 2.

## API hardening

- CORS allowlist via `CORS_ORIGINS`.
- Rate limiting on login/refresh.
- Parameterized SQL via SQLAlchemy.
- Centralized error handlers — no stack traces in production responses.
- Request IDs for correlation (`X-Request-ID`).

## Logging

Do **not** log:

- Passwords, tokens, Authorization headers
- Email bodies, document contents, secrets

Sensitive key redaction filter is installed on the root logger.

## Data handling

- Source systems (Gmail/Drive/Dropbox) remain system of record for binaries.
- Audit ledger is append-only.
- Automation proposes; humans approve uncertain actions.

## IDOR / matter access

- Always authorize by authenticated user + permission + matter ACL (Phase 2).
- Never trust client-supplied “acting as” user IDs.

## OAuth integrations (upcoming)

- Store tokens encrypted at rest.
- Support expiry, refresh, and revocation.
- Least-privilege scopes only.
