---
Date: 2026-05-10
Change: nas-https
Status: REVIEWED
HAS_UI_SURFACE: yes
---

# nas-https Requirements

## Goals

- Real CA-trusted TLS on the NAS-hosted python-agent so the browser address bar shows 🔒 (no click-through warning) and Google's GSI library runs.
- Cert provisioning via **Tailscale** (Let's Encrypt issued through Tailscale's DNS-01 challenge). Hostname becomes `python-agent.<tailnet-id>.ts.net`.
- Flip `SESSION_COOKIE_SECURE` back to its default `true` — session cookies will only traverse HTTPS, eliminating the LAN-sniff risk the multi-user-auth-core change deferred to this one.
- Enable **Google Sign-In on NAS** — frontend's GSI button is already conditional on `config.has_google && (HTTPS || localhost)`; once HTTPS is real, setting `GOOGLE_CLIENT_ID` in NAS env makes the button live.
- Provide a small read-only **`/admin/cert` page** (admin role only) showing tailnet hostname + cert expiry + days remaining + Tailscale connection status + last renew time. This is the `HAS_UI_SURFACE: yes` artifact.
- Lay the foundation for the future `cloud-deploy` and `nas-funnel` changes — same code path, just swap Tailscale `serve` for `funnel` (one command) or front it with a public domain.

## Non-Goals

- **Family device management UI** — Tailscale's official admin console at `login.tailscale.com` already handles invites, device list, ACLs. Re-implementing it inside python-agent is duplicate work.
- **Cert renewal in-app** — Tailscale daemon auto-renews. `/admin/cert` is read-only; no manual-renew button.
- **Public access via Funnel** — separate future change `nas-funnel`. Flipping `tailscale serve` → `tailscale funnel` is one command, deferred.
- **Cloud deployment** — separate future change `cloud-deploy`. This change makes it possible, doesn't ship it.
- **Buying a custom domain** — Tailscale's `*.ts.net` hostname is acceptable; users access via Tailscale-installed devices.
- **LAN plain-HTTP fallback** — the existing `10.0.0.20:8910` plain HTTP port is intentionally removed. Single entry point through tailnet HTTPS. Emergency recovery is via NAS host shell (UGOS terminal), not via plain HTTP.
- **Adding Caddy / Traefik / a separate reverse-proxy container** — `tailscale serve` does TLS termination directly; frontend nginx still serves the SPA + proxies `/api/*` to the backend internally.
- **Migrating in-flight `multi-user-auth-admin-ui`** — that change is on `spec-driven` schema; it continues independently.

## Constraints

- **Hard: Runs on UGREEN UGOS Pro (NAS host OS).** Tailscale must be installable from UGOS App Center (it is — verified pre-design).
- **Hard: No domain purchase required.** The tailnet hostname is the canonical URL.
- **Hard: Family must be able to access from outside home (cellular).** This is automatic on tailnet — Tailscale provides anywhere-to-anywhere connectivity for tailnet members. The "LAN-only" framing is about origin model (no public internet exposure), not physical location.
- **Hard: All existing sessions invalidate at cutover** — host name changes (`10.0.0.20:8910` → `python-agent.<tailnet-id>.ts.net`) AND `SESSION_COOKIE_SECURE` flips true. Family members must re-login after the cutover. Acceptable; one-time pain.
- **Hard: No `tailscale serve` config in git** — the serve config lives in `/var/lib/tailscale` on the NAS host. Document the one-time setup command in CLAUDE.md so re-applying after a host wipe is reproducible.
- **Soft: Minimize moving parts.** No new Docker container if `tailscale serve` can do the job (it can). UGOS daemon takes care of cert renewal + restart.
- **Soft: Keep what's git-tracked.** `docker-compose.prod.yml` port mapping changes go in git. `tailscale up` / `tailscale serve` commands go in CLAUDE.md.

## Success Criteria

1. `curl -v https://python-agent.<tailnet-id>.ts.net/api/auth/config` from a tailnet device returns HTTP 200 with a valid Let's Encrypt cert chain (no `--insecure` flag needed).
2. Loading the URL in Chrome/Safari/Firefox on a Tailscale-connected device shows 🔒 + green address bar without warning.
3. NAS `.env` has `SESSION_COOKIE_SECURE=true` (line removed or explicitly true) and `austin.xyz@gmail.com` can still log in via email+password.
4. With `GOOGLE_CLIENT_ID` set in NAS env, the LoginView GSI button appears and Google Sign-In completes successfully (creates session, lands on `/chat`).
5. `/admin/cert` page (admin-only, member redirects away):
   - Shows hostname `python-agent.<tailnet-id>.ts.net`
   - Shows cert expiry date and "X days remaining" badge (green if >30d, yellow 7-30d, red <7d)
   - Shows Tailscale status (`online` / `offline` / `error`)
   - Shows last renewal time (from Tailscale's cert metadata)
6. A family member on a phone using cellular data (NOT on home WiFi) can log in via the tailnet URL — proves tailnet connectivity works off-LAN.
7. Old `http://10.0.0.20:8910` URL no longer responds (port mapping removed). `tailscale serve` on `:443` is the only port published to family.
8. `npm run e2e:integration` still passes on the dev stack (no regression to the local dev flow which keeps plain HTTP).

## User Stories

- **As the admin (austin)**, I want to access python-agent securely from any device (home laptop, work laptop, phone on cellular) without exposing my NAS to the public internet, so my session cookies + auth posture meet the standard the multi-user-auth design deferred to this change.
- **As a family member (e.g., bucolic)**, I want to install Tailscale once on my phone and then access python-agent at the same HTTPS URL from anywhere — home WiFi, coffee shop, cellular — without having to remember a different URL or VPN config per location.
- **As the admin**, I want a quick `/admin/cert` glance in the app to know "TLS is healthy + Tailscale is connected" so I don't have to log into the Tailscale admin console just to confirm everything's up.
- **As the admin**, I want to enable Google Sign-In as a one-click login option for family members who'd rather not remember another password.
- **As a future-me deploying to cloud**, I want this change's reverse-proxy + cookie + admin-UI patterns to be reusable so `cloud-deploy` is mostly a hostname swap, not a redesign.

## Open Questions

All open questions resolved in Phase 3 brainstorming review (2026-05-10):

- **Q-01 RESOLVED:** OAuth client creation (Google Cloud Console) → **include as a manual ops checkbox in `tasks.md`** so the workflow surfaces it during apply. Documented in CLAUDE.md is not enough — easy to forget. Admin checks the box once the client ID is in NAS `.env`.
- **Q-02 RESOLVED:** `tailscale serve` config in `/var/lib/tailscale` (non-git) → **document the one-time setup command in CLAUDE.md's NAS Deployment section**. Both `tailscale up` and `tailscale serve --https=443 http://localhost:8910` go in.
- **Q-03 RESOLVED:** `<tailnet-id>` is **deployment-time data, not design-time**. Apply-phase task 1 is "sign up for Tailscale, install on NAS, capture tailnet-id"; subsequent tasks fill it into `.env` and the requirements doc's locked-but-templated `APP_BASE_URL` value.
- **Q-04 RESOLVED:** Session invalidation at cutover → **no banner; rely on standard `/login` redirect**. Document the one-time re-login expectation in the dev log entry for the cutover day. Family scale (2-5 users) doesn't warrant UX engineering for a once-ever event.

## Referenced Capabilities

- **MODIFY `multi-user-auth`**:
  - `SESSION_COOKIE_SECURE=true` (currently false on NAS only)
  - ADD a new SHALL clause for the `/admin/cert-status` API endpoint (admin-only, returns `{hostname, cert_expiry_iso, days_remaining, tailscale_status, last_renew_iso}`)
- **MODIFY `frontend-scaffold`**:
  - ADD route `/admin/cert` (admin-only, redirects member → `/chat`)
  - The existing GSI button conditional logic stays unchanged; only behavior changes because `window.location.protocol` becomes `https:` on NAS
- **ADD `nas-https` (new capability)**:
  - SHALL clauses covering: Tailscale serve on `:443` terminating TLS, `tailscale cert` provisioning, the read-only admin cert page, removal of the `10.0.0.20:8910` plain HTTP port mapping
