---
Date: 2026-05-10
Change: nas-https
HAS_UI_SURFACE: yes
Requirements: docs/superpowers/specs/2026-05-10-nas-https-requirements.md
Mocks: docs/superpowers/specs/mocks/2026-05-10-nas-https-mocks.html
---

## Why

The NAS-hosted python-agent runs on plain HTTP at `http://10.0.0.20:8910`, which forced `multi-user-auth-core` to ship with `SESSION_COOKIE_SECURE=false` (session cookies traverse LAN unencrypted) and to disable Google Sign-In on NAS (Google's GSI library refuses to load on HTTP origins). This change brings real CA-trusted HTTPS to the NAS via Tailscale's auto-Let's-Encrypt mechanism, closing both gaps and laying the foundation for the future `cloud-deploy` and `nas-funnel` changes.

## What Changes

- **NEW** Tailscale daemon on NAS host (installed via UGOS App Center), joining a personal tailnet. NAS gets hostname `python-agent.<tailnet-id>.ts.net`.
- **NEW** `tailscale serve --https=443 http://localhost:8910` runs as a NAS-host service, terminating TLS on `:443` and reverse-proxying to the existing frontend nginx container on port 8910.
- **BREAKING** `docker-compose.prod.yml` removes the `8910:3000` port mapping. The plain-HTTP entry point at `http://10.0.0.20:8910` no longer responds. Family members can ONLY reach the app via the new HTTPS URL after installing Tailscale on their devices.
- **BREAKING** NAS `.env` flips `SESSION_COOKIE_SECURE=false` → removes the line (back to default `true`) and sets `APP_BASE_URL=https://python-agent.<tailnet-id>.ts.net`. All existing sessions invalidate; family members re-login once.
- **NEW** `GOOGLE_CLIENT_ID` is configured in NAS `.env`. Google Sign-In becomes available on NAS (GSI button shows in LoginView when both `config.has_google` AND `(HTTPS || localhost)` are true; HTTPS becomes true after this change).
- **NEW** Admin-only API endpoint `GET /api/admin/cert-status` returns `{hostname, cert_expiry_iso, days_remaining, tailscale_status, last_renew_iso}`. Reads from Tailscale CLI / cert file metadata via `subprocess`.
- **NEW** Frontend route `/admin/cert` (admin-only, router guard redirects member → `/chat`) displaying the cert status card per the locked tokens + verbatim text in `docs/superpowers/specs/mocks/2026-05-10-nas-https-mocks.html`.
- **NEW** Sidebar nav (desktop) and `/me` (mobile) gain a conditional "证书与 Tailscale 状态" link visible only to admin users. Member view unchanged.
- CLAUDE.md gets a new section under NAS Deployment documenting the one-time Tailscale setup commands (`tailscale up`, `tailscale serve …`) and a new pitfall: "`tailscale serve` config lives in `/var/lib/tailscale` on the NAS host, not in git — re-run the setup command after a host wipe".

## Capabilities

### New Capabilities

- `nas-https` — the act of terminating TLS via Tailscale serve, exposing the cert status admin API, and removing the plain-HTTP LAN entry point. Becomes a new `openspec/specs/nas-https/spec.md` after archive.

### Modified Capabilities

- `multi-user-auth` — flips `SESSION_COOKIE_SECURE` default back to `true` on NAS deploy. Adds the new `/api/admin/cert-status` endpoint as an admin-only authenticated API.
- `frontend-scaffold` — adds router entry `/admin/cert` with the existing admin guard. Adds conditional admin link in the AppLayout sidebar (desktop) and MeView (mobile). The GSI button's conditional logic stays unchanged; only the operational world (`window.location.protocol === 'https:'` on NAS) changes.

## Impact

- **Files added (backend):** `backend/app/routes/admin.py` (or extend an existing admin blueprint) for `GET /api/admin/cert-status`. New service helper `backend/app/services/tailscale_service.py` wrapping `tailscale status --json` and reading the cert file metadata.
- **Files added (frontend):** `frontend/src/views/AdminCertView.vue`. `frontend/src/stores/admin.js` (or extend existing if present) for fetching cert status.
- **Files modified (backend):** none except `routes/__init__.py` to register the new blueprint.
- **Files modified (frontend):** `router/index.js` (new `/admin/cert` route + admin guard), `AppLayout.vue` (conditional admin nav item), `MeView.vue` (conditional admin link). No changes to `LoginView.vue` (GSI conditional already handles HTTPS detection).
- **Files modified (config / ops):** `docker-compose.prod.yml` (remove `8910:3000` port mapping). NAS `.env` (remove `SESSION_COOKIE_SECURE`, set `APP_BASE_URL`, set `GOOGLE_CLIENT_ID`).
- **Files modified (docs):** `CLAUDE.md` (NAS Deployment section: Tailscale setup), `docs/log/2026-05-10.md` (or whatever date this ships) documenting the cutover.
- **External setup (manual, one-time, captured as a task in `tasks.md`):**
  - Sign up for Tailscale (free personal tier), capture tailnet-id
  - Install Tailscale on NAS via UGOS App Center
  - `tailscale up` (auth via Google SSO)
  - Enable HTTPS in Tailscale admin console
  - `tailscale serve --https=443 http://localhost:8910` (config persists on NAS host)
  - Create Google OAuth client at console.cloud.google.com (authorized redirect URI = `https://python-agent.<tailnet-id>.ts.net`)
  - Push new image, update NAS `.env`, UGOS pull + apply
  - Notify family + send them Tailscale invitation links
- **Operational:** family members must install Tailscale on their devices (one-time, ~5 min per device). Old URL `http://10.0.0.20:8910` no longer works. All sessions invalidate; one re-login per family member.

## Out of Scope

- **Public access via Tailscale Funnel** — deferred to `nas-funnel` change. `tailscale serve` → `tailscale funnel` is a one-line flip once HTTPS works.
- **Cloud deployment** — deferred to `cloud-deploy` change. Same code path will be reused behind a public domain instead of Tailscale.
- **Family-device management UI inside python-agent** — Tailscale's own admin console at `login.tailscale.com` handles device list + invites + ACLs. Re-implementing is duplicate work.
- **Manual cert renewal button** — Tailscale daemon auto-renews. `/admin/cert` is read-only.
- **Buying / configuring a custom domain** — Tailscale's `*.ts.net` hostname is the canonical URL.
- **Adding Caddy / Traefik / a separate reverse-proxy container** — `tailscale serve` does the TLS+reverse-proxy job; no new container needed.
- **LAN plain-HTTP fallback** — single entry through tailnet HTTPS. Emergency recovery is via NAS host shell, not via plain HTTP.
- **Tailscale ACL configuration** — default "every tailnet member can reach every device" is fine for family scale. ACL hardening (e.g., per-user, per-device) deferred to a future hardening change.
- **Migrating in-flight `multi-user-auth-admin-ui`** — that change is on `spec-driven` schema; it continues independently.
