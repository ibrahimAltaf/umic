# API Documentation

Base URL (local): `http://localhost:8000`  
Version prefix: `/api/v1`  
Interactive docs: `/docs` (disabled pattern ready for production lockdown)

## Conventions

- JSON request/response
- Bearer JWT for protected routes
- Errors:

```json
{
  "error": {
    "code": "authentication_error",
    "message": "Invalid email or password",
    "details": {},
    "request_id": "uuid"
  }
}
```

- Pagination (list endpoints): `page`, `page_size`, response includes `total`, `pages`

## Health

### `GET /health`

Returns `{ "status": "ok", "service": "api", "environment": "..." }`

## Auth — `/api/v1/auth`

| Method | Path | Auth | Description |
| --- | --- | --- | --- |
| POST | `/login` | No | Email/password → access + refresh |
| POST | `/refresh` | No | Rotate refresh token |
| POST | `/logout` | Yes | Revoke refresh token |
| POST | `/logout-all` | Yes | Revoke all refresh tokens |
| GET | `/me` | Yes | Current user + roles + permissions |
| POST | `/password-reset/request` | No | Enumeration-safe stub |

### Login body

```json
{ "email": "admin@example.com", "password": "ChangeMeAdmin123!" }
```

### Token response

```json
{
  "access_token": "...",
  "refresh_token": "...",
  "token_type": "bearer",
  "expires_in": 900
}
```

Rate limits: login `5/minute`, refresh `20/minute` (SlowAPI).

## Users — `/api/v1/users`

Requires permissions `users:read` / `users:write`.

| Method | Path | Description |
| --- | --- | --- |
| GET | `/users` | Paginated list (`search` optional) |
| POST | `/users` | Admin-provisioned registration |
| PATCH | `/users/{id}` | Update profile / active / roles |

## Roles & permissions

| Method | Path | Permission |
| --- | --- | --- |
| GET | `/roles` | `roles:read` |
| GET | `/permissions` | `permissions:read` |

## Planned modules (Phase 2+)

`/matters`, `/matter-types`, `/entities`, `/entity-types`, `/relationships`, `/review-queue`, `/audit-events`, `/integrations`

## Authorization notes

- Backend enforces all permission checks.
- Disabled users cannot login or refresh.
- Refresh tokens are hashed at rest and rotated on use.
- Logout revokes the presented refresh token.
