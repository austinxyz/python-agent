## Context

The NAS-hosted python-agent has run on plain HTTP at `http://10.0.0.20:8910` since the `nas-deployment` change. The `multi-user-auth-core` change explicitly deferred two related items to a future `nas-https`:

1. `SESSION_COOKIE_SECURE=false` workaround so session cookies traverse the LAN unencrypted (the only way they survive plain HTTP).
2. Google Sign-In disabled on NAS because Google's GSI library refuses to load on HTTP origins.

The user explicitly chose (in `/opsx:explore` Phase 1) to address BOTH gaps plus admin UI for cert status plus cloud-deploy readiness in a single change. The chosen access model is LAN-only (or rather, tailnet-only — Tailscale provides anywhere-to-anywhere connectivity for tailnet members, so "LAN" is the threat model not a physical constraint). A future `nas-funnel` change can flip `tailscale serve` → `tailscale funnel` to expose the same hostname publicly without re-architecting.

V1 scale: family-scale install (5-10 family members), LAN-physical-network anchor (the NAS is at home), Tailscale tailnet for off-LAN reach. Decisions favor minimal moving parts.

## Goals / Non-Goals

**Goals:**

- Real CA-trusted TLS on the NAS via Tailscale's auto-Let's-Encrypt (no self-signed, no per-device CA install).
- Single canonical hostname `python-agent.<tailnet-id>.ts.net`. Same URL works on home WiFi, cellular, coffee-shop WiFi — anywhere Tailscale is connected.
- Flip `SESSION_COOKIE_SECURE` back to default `true` (HTTPS-only).
- Enable Google Sign-In on NAS (provide `GOOGLE_CLIENT_ID`; GSI button auto-appears in LoginView).
- Provide a small read-only `/admin/cert` page so admin can verify cert + Tailscale health without leaving the app.
- Reusable foundation for `cloud-deploy` and `nas-funnel`.

**Non-Goals:**

- Public access via Funnel (separate `nas-funnel` change).
- Cloud deployment (separate `cloud-deploy` change).
- Family-device management UI in python-agent (Tailscale admin console suffices).
- Manual cert renewal button (Tailscale daemon auto-renews).
- Custom domain (Tailscale's `*.ts.net` hostname is canonical).
- Caddy/Traefik (Tailscale serve does both TLS termination and reverse proxy).
- LAN plain-HTTP fallback (single entry through tailnet HTTPS).
- Tailscale ACL hardening (default "every tailnet member can reach everything" is acceptable for family).
- Retroactively reformatting in-flight changes (`multi-user-auth-admin-ui` stays on `spec-driven`).

## Decisions

### 1. Cert source: Tailscale-issued Let's Encrypt (not self-signed, not user-domain DNS-01)

**Choice:** Use `tailscale cert` (under the hood: Tailscale runs the ACME DNS-01 challenge against `<tailnet-id>.ts.net`) to provision a publicly-trusted Let's Encrypt cert for `python-agent.<tailnet-id>.ts.net`.

**Alternatives considered:**

- *Self-signed cert + per-device CA install:* zero external dependencies but per-device install pain (each family phone, laptop) AND Google's GSI library still refuses to run (it requires a publicly-trusted CA chain). Rules itself out the moment "Google Sign-In on NAS" is a goal.
- *Caddy's internal CA (similar to mkcert):* same per-device install problem; same GSI refusal.
- *User-owned domain + DNS-01 via Caddy + acme.sh:* works but requires (a) buying a domain ($10-15/yr), (b) DNS API credentials in a NAS config file, (c) the hostname is public DNS revealing internal LAN topology. Tailscale eliminates all three by providing a hostname that resolves to a private 100.x.x.x IP useless without Tailscale.

**Why Tailscale:** zero domain purchase, zero DNS API setup, browser-trusted cert, A→B (Funnel) is a one-command flip. Free personal tier handles 100 devices.

### 2. Reverse proxy: `tailscale serve` (not Caddy in a Docker sidecar)

**Choice:** Use `tailscale serve --https=443 http://localhost:8910` directly on the NAS host. No Caddy container, no Traefik, no nginx reverse-proxy add-on.

**Alternatives considered:**

- *Caddy as a Docker sidecar in `docker-compose.prod.yml`:* keeps config in git, portable to other hosts. But adds an extra container, an extra config file (Caddyfile), an extra cert-renewal daemon (Caddy + Tailscale both running ACME). Tailscale serve provides path-pattern routing if needed (we don't — frontend nginx already proxies `/api/*` internally on port 8910), so Caddy adds zero capability.
- *Tailscale daemon in a Docker sidecar (rather than host install):* would require `network_mode: service:tailscale` for frontend to share its network namespace, or jury-rigged port forwarding. Either path is fiddly. Host install is the documented way to use `tailscale serve` on a server.

**Why host-native Tailscale serve:** least moving parts, fewest config files, no double-ACME, UGOS App Center manages daemon lifecycle + auto-start.

### 3. Install location: UGOS App Center (not Docker compose service)

**Choice:** Install Tailscale via UGREEN UGOS Pro's App Center. The Tailscale daemon runs as a system service on the NAS host.

**Alternatives considered:**

- *Docker sidecar (`tailscale/tailscale` image in docker-compose.prod.yml):* keeps the entire deployment in `docker-compose up`. But — as discussed in Decision 2 — running `tailscale serve` for another container's port requires network-namespace sharing tricks. Host install is simpler and UGOS already supports it.
- *Manual install via `apt install tailscale` on NAS shell:* works but bypasses UGOS's app-management UI. Less discoverable for future maintainers; updates require manual `apt upgrade`. UGOS App Center version auto-updates.

**Why UGOS-native:** UGOS handles daemon start/stop/restart, App Center handles version upgrades, native integration with UGOS Docker Project UI (which the rest of the deployment uses). Cost: Tailscale config isn't in git — but `tailscale up` and `tailscale serve` are one-time setup commands documented in CLAUDE.md.

### 4. Admin UI scope: read-only status card (no renew button, no device management)

**Choice:** `/admin/cert` shows hostname + cert expiry + days remaining + Tailscale connection status + last renew time. No buttons. Polls `GET /api/admin/cert-status` every 60 seconds.

**Alternatives considered:**

- *Add a "Renew now" button:* Tailscale daemon auto-renews well before expiry (default 30 days before). Manual renew is a niche operation that's better handled via NAS shell (`tailscale cert --renew`) than via a button in the app. A button means Flask runs `subprocess` against a privileged command — increases attack surface for negligible benefit.
- *Show family device list + invite-link generator:* duplicates Tailscale's own admin console at `login.tailscale.com`. Admin already uses that console to approve devices and create tags. Re-implementing inside python-agent is hundreds of lines for zero new capability.
- *No admin UI at all (skip /admin/cert):* would technically satisfy goals (a)+(b)+(c) but the user explicitly chose `HAS_UI_SURFACE: yes` in `/opsx:explore`. A small read-only page is the agreed-on scope.

**Why minimal:** the value is "at-a-glance health check from inside the app I already have open." Anything actionable (renew, invite, debug) is better done in the Tailscale console.

### 5. Plain HTTP removed entirely (no LAN fallback)

**Choice:** `docker-compose.prod.yml` removes the `8910:3000` port mapping. Tailscale serve at `:443` is the only published entry point. Emergency recovery is via NAS host shell.

**Alternatives considered:**

- *Keep `8910:3000` mapping for LAN-internal recovery:* would let an admin bypass Tailscale in emergencies but creates a second cookie-incompatible entry (plain HTTP → `Secure` flag rejects the cookie → admin has to log in again on the alt URL anyway). And it doubles the attack surface.
- *Bind `127.0.0.1:8910` only (NAS-host loopback):* this is functionally what happens after the change — the frontend container exposes port 80 (or 3000), Tailscale serve reads `localhost:8910`. The compose file just doesn't publish 8910 to the LAN. Either way, no LAN-external access.

**Why drop entirely:** single canonical URL means single cookie context means no "Secure cookie won't follow you to the alt URL" gotcha. Tailscale daemon is reliable; the rare daemon outage is recoverable via UGOS shell.

### 6. Session invalidation on cutover: no banner, just standard /login redirect

**Choice:** At cutover, all existing sessions become invalid (hostname changes from `10.0.0.20:8910` to `python-agent.<tailnet-id>.ts.net`, AND `Secure` flag flips from false to true). Users hitting any authenticated route get the standard `/login?redirect=...` redirect. No special banner, no special messaging.

**Alternatives considered:**

- *Show a "Re-login required after HTTPS upgrade" banner once:* small UX polish for a one-time event affecting 2-5 family members. Engineering and testing cost > benefit.
- *Server-side migrate sessions to new domain:* not technically possible (cookie domain is set by the browser based on the response host).

**Why nothing:** 5 family members, one-time event, login form is the answer regardless. Document the cutover expectation in dev log + a note to family members ("after I push the new image, you'll need to log in again — open the new URL").

### 7. Google OAuth client creation: in tasks.md as a manual ops checkbox

**Choice:** `tasks.md` includes a task "Create Google OAuth client in Google Cloud Console" with detailed steps (project, OAuth consent screen, client type, authorized redirect URI = `https://python-agent.<tailnet-id>.ts.net`). Admin runs through it manually, checks the box once `GOOGLE_CLIENT_ID` is in NAS `.env`.

**Alternatives considered:**

- *Skip Google OAuth setup (treat as out-of-band documentation in CLAUDE.md):* would split the work — "deploy nas-https then separately set up Google login when you remember to." Manual setup is forgotten. Better to wire it into the apply phase so the workflow surfaces it.

**Why in tasks:** apply phase walks tasks one by one. A manual OPS task is fine as long as it has a checkbox + clear instructions. Family members start using Google login the same day NAS goes HTTPS.

## Risks / Trade-offs

- **R-01 — Tailscale daemon down on NAS = app unreachable.** Mitigation: Tailscale is reliable (uptime track record is strong); UGOS auto-starts the daemon on boot. Recovery path: UGOS terminal → `tailscale up` → `tailscale serve status` to verify. Document in CLAUDE.md.

- **R-02 — Family device without Tailscale installed = no access.** Mitigation: this IS the access model. Tailscale install is 5 minutes per device, one-time. Admin sends invite link, family signs in with their own Google account, device joins tailnet. Document in CLAUDE.md + send family a one-page setup guide.

- **R-03 — Tailscale free tier limits.** Free personal tier: 100 devices, 3 users (where "user" = a Tailscale account). Family of 5 = 5 Tailscale accounts (each invited family member uses their own account). 5 ≤ 3? **Conflict.** Check Tailscale's current free-tier user limit (it has been 3 for a while but may have been raised). If still 3, options: (a) admin shares one account across family (defeats audit trail), (b) admin upgrades to a paid plan (~$5/user/month), (c) defer Google-account-per-family-member to future and have all family devices sign in to one Tailscale account. **Open issue: confirm Tailscale free-tier user limit before apply** — see Open Questions.

- **R-04 — `tailscale serve` config not in git.** Mitigation: document the one-time setup command in CLAUDE.md. Re-running it is idempotent. Risk is small for a NAS that doesn't get re-imaged.

- **R-05 — Tailscale outage on Tailscale's side blocks app even though NAS is up.** Tailscale relies on its coordination server (`controlplane.tailscale.com`) to discover peers, BUT once a tailnet connection is established it doesn't need the coordination server until reconnect. A coordination-server outage during an active session is invisible. Only matters during reconnect or new-device-onboarding. Mitigation: it's Tailscale's problem, not ours; their uptime is excellent. Not a foreseeable risk.

- **R-06 — Browser cert pinning of old cert across hostname change.** No-op. The change isn't replacing a cert, it's introducing a cert where there was none. Old plain-HTTP cache doesn't have a cert to pin.

- **R-07 — `/api/admin/cert-status` invokes `subprocess` to call `tailscale` CLI.** Attack surface. Mitigation: the endpoint takes no user input; the subprocess command is hard-coded (`tailscale status --json`); admin role required; output is parsed not echoed. No injection vector.

## Migration Plan

1. **Pre-flight (admin, before any code changes):**
   - Sign up for Tailscale free personal account at tailscale.com (uses Google SSO).
   - Capture the tailnet-id (visible in the admin console after signup).
   - Verify Tailscale free-tier user limit covers the family size (R-03). If not, decide single-account vs paid plan.

2. **NAS-side setup (admin, manual, one-time):**
   - UGOS App Center → install Tailscale.
   - On NAS shell: `tailscale up` (will open a browser-auth flow on a Tailscale-connected device).
   - Tailscale admin console → enable HTTPS for the tailnet.
   - On NAS shell: `tailscale cert python-agent.<tailnet-id>.ts.net` (verify cert provisions).
   - On NAS shell: `tailscale serve --https=443 http://localhost:8910` (sets up the reverse proxy; persists across reboots).

3. **Google OAuth client (admin, manual, one-time):**
   - Create OAuth client at console.cloud.google.com → APIs & Services → Credentials.
   - Authorized redirect URI: `https://python-agent.<tailnet-id>.ts.net/api/auth/login/google/callback` (or whatever path the backend exposes; verify against current `multi-user-auth` spec).
   - Authorized JS origins: `https://python-agent.<tailnet-id>.ts.net`.
   - Capture `GOOGLE_CLIENT_ID`.

4. **Code changes (this OpenSpec change):**
   - Backend: add `routes/admin.py` with `GET /api/admin/cert-status`. Add `services/tailscale_service.py` wrapping `tailscale status --json` subprocess.
   - Frontend: add `views/AdminCertView.vue`. Register `/admin/cert` route in router. Add conditional admin nav slot in AppLayout + MeView.
   - Tests: backend pytest cases (admin 200, member 403, unauth 401, Tailscale-down 200 with offline status). Frontend vitest cases (token+text locks, polling, three states).
   - Docker: `docker-compose.prod.yml` removes `8910:3000` mapping.
   - Docs: CLAUDE.md NAS Deployment section gets Tailscale setup commands + pitfall about `/var/lib/tailscale` not being in git.

5. **Ship (cutover):**
   - `./scripts/build-and-push.sh` (new images).
   - Update NAS `.env`: remove `SESSION_COOKIE_SECURE`, set `APP_BASE_URL=https://python-agent.<tailnet-id>.ts.net`, set `GOOGLE_CLIENT_ID=...`.
   - UGOS Docker → python-agent → Pull → Apply.
   - Verify on tailnet device: `https://python-agent.<tailnet-id>.ts.net` loads, GSI button visible, login works, `/admin/cert` shows healthy state.

6. **Family onboarding (admin → family, one per device):**
   - Send each family member: a Tailscale invitation link + a one-paragraph note ("install Tailscale, sign in with your Google account, then open https://python-agent.<tailnet-id>.ts.net and re-login").
   - Each family member: install Tailscale (~3 min), accept invite, open URL, re-login.

7. **Verification:**
   - Admin in browser 1: cell-on-wifi: app works.
   - Admin in browser 2: cell-on-cellular (turn off WiFi): app works (proves it's not LAN-IP).
   - Family member: same.
   - `/admin/cert` shows hostname + cert expiry + Tailscale: online.

**Rollback plan:** if the new image breaks, revert the NAS deploy to the previous image tag (UGOS Docker → edit compose file → change tag → Apply). To bring back plain HTTP temporarily, re-add `8910:3000` to `docker-compose.prod.yml` and put `SESSION_COOKIE_SECURE=false` back in `.env`. Tailscale serve doesn't have to be turned off — it just becomes dual-entry (HTTPS via tailnet AND HTTP on LAN). Avoid for security but available for emergencies.

## UI Fidelity

Implementation MUST follow `docs/superpowers/specs/mocks/2026-05-10-nas-https-mocks.html` for all visual elements.

**Mock anchors used:**

- `#admin-cert-desktop` — healthy state card layout (desktop)
- `#admin-cert-warning` — 7-30d remaining state (yellow tokens)
- `#admin-cert-tailscale-down` — Tailscale offline state (red tokens)
- `#admin-cert-mobile` — mobile equivalent (393px-wide)

**Locked Notion design tokens (frontend tests assert via `wrapper.classes()`):**

- Card: `bg-notion-canvas`, `border-notion-hairline`, `rounded-lg`
- Status pills:
  - 健康: `bg-notion-tint-mint`, `text-notion-brand-green`
  - 即将到期: `bg-notion-tint-yellow`, `text-notion-warning`
  - 异常 / 紧急: `bg-notion-tint-rose`, `text-notion-error`
- Row label: `text-notion-steel`, `text-[13px]`
- Row value: `text-notion-charcoal`, `font-mono`, `text-[12px]`

**Locked verbatim text strings (frontend tests assert via `wrapper.text()`):**

- Card title: `证书与 Tailscale 状态`
- Row labels: `Tailnet 主机名`, `证书到期`, `Tailscale 连接`, `上次 renew`
- Status pills: `健康`, `即将到期`, `异常`
- Days remaining: `还剩 N 天` format
- Error suggestion text: `SSH 进 NAS，跑 tailscale status 排查。`

**Layout invariants:**

- Card max-width: ~560px on desktop, 100% on mobile (<393px)
- Page renders inside AppLayout (sidebar visible at md+)
- Polling interval: 60s (NOT user-configurable in V1)
- No actionable buttons (no Renew, no Refresh, no Edit)

## Open Questions

- **Q-01 (open, not blocking design):** Tailscale free personal tier user limit — last documented as 3 users. Family of 5 means 2 users out. Admin should confirm during the pre-flight task (migration step 1) before committing to the design. Fallbacks documented in R-03.
- **Q-02 (open, not blocking design):** Does the OAuth client need explicit "consent screen" approval in Google Cloud Console for users outside the developer's organization? For a personal-tier OAuth app with internal-only family use, Google's "Testing" user-cap (100 users) and "Test users" allowlist is fine — won't need to publish the app for verification. Admin adds each family member's Google email as a Test User. Confirm during task 3 of the migration plan.
