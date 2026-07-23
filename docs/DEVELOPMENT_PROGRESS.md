# Development Progress

**Updated:** 2026-07-24  
**Status:** A–Z product complete (client credentials required for live Google/Dropbox accounts)

## Complete

- Auth, RBAC, audit, password reset request/confirm, migrations `001`–`005`
- Matters (full tabs + create/edit with confidential/privileged/aliases)
- Matter ACL: personal / confidential / privileged
- Entities create/list/edit + link/unlink on matters
- Review Kanban, discrepancies (global + matter), billing propose/approve
- Expenses/mileage, Gmail + Drive sync, Dropbox OAuth + token paths
- Search (FTS + ACL), summaries, T&E Sheets export
- Document extract (PDF + optional image OCR), duplicates, batch extract
- Celery sync + hourly beat schedule, workers call real SyncService
- Users create/disable, roles, audit, settings, polished UI

## Client must provide (for their live data)

| Item | Why |
| --- | --- |
| Google OAuth Client ID + Secret | Live Gmail / Drive / Sheets |
| Dropbox App Key + Secret **or** access token | Live Dropbox sync |
| Which Google / Dropbox accounts & folders | Correct mailbox and files |

## Login (local demo)

- http://localhost:3000 — `admin@example.com` / `ChangeMeAdmin123!`
