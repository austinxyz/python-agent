## 1. Pre-flight: Tailscale + OAuth setup (manual ops)

> These tasks are admin-driven shell/web operations, not code. They precede all backend/frontend work because they produce values (tailnet-id, GOOGLE_CLIENT_ID) needed in `.env` and in the OAuth redirect URI.

- [x] 1.1 Sign up for Tailscale free personal account at tailscale.com (Google SSO). Capture the tailnet-id from the admin console URL (looks like `tail-abc123`). Record it as `TAILNET_ID` in your local notes.
- [x] 1.2 **VERIFY Tailscale free-tier user limit** — log into Tailscale admin console → Billing/Plan. Confirm the current free-tier user limit ≥ family size (2 admin + bucolic + future). If limit < family size, decide: (a) all family devices use admin's single account (cleanest), (b) upgrade to paid plan. Document the decision in `docs/log/<today>.md`.
- [x] 1.3 On NAS host (UGOS terminal or SSH): UGOS App Center → install Tailscale. Verify daemon starts: `tailscale status` (will say "Logged out" until 1.4).
- [x] 1.4 On NAS shell: `tailscale up` — opens auth URL on stdout; open it on a browser-already-logged-into-Tailscale (admin's laptop). Approve the NAS as a tailnet device.
- [x] 1.5 In Tailscale admin console: DNS settings → enable "HTTPS Certificates" for the tailnet. (This is the toggle that authorizes Tailscale to provision Let's Encrypt certs on your behalf.)
- [x] 1.6 On NAS shell: `tailscale cert python-agent.<TAILNET_ID>.ts.net` — verify it returns the cert + key file paths (under `/var/lib/tailscale/certs/`). If it fails, debug per Tailscale docs (DNS-01 challenge timing).
- [x] 1.7 Create Google OAuth client at https://console.cloud.google.com/apis/credentials → "Create OAuth client" → type = Web application. Authorized JavaScript origins: `https://python-agent.<TAILNET_ID>.ts.net`. Authorized redirect URIs: `https://python-agent.<TAILNET_ID>.ts.net` (the Google login flow uses Google Identity Services in-browser; check the existing `multi-user-auth` spec for whether a backend redirect is also needed). Capture `GOOGLE_CLIENT_ID`.
- [x] 1.8 Add family Google email addresses as "Test users" on the OAuth consent screen (so Google's "unverified app" warning doesn't block them). Keep app status as "Testing" — not "In production" (avoids the verification gauntlet for an internal-only app).
- [x] 1.Z Run superpowers:requesting-code-review on the diff for group 1 — **N/A: no code in this group**. Skip this checkpoint and proceed to group 2.

## 2. Backend: `/api/admin/cert-status` endpoint + Tailscale service helper

- [x] 2.1 RED — `backend/tests/test_admin_routes.py`: 4 cases for `GET /api/admin/cert-status` — admin 200 with valid JSON shape (5 fields: hostname, cert_expiry_iso, days_remaining, tailscale_status, last_renew_iso); member 403 `{"error": "admin required"}`; unauthenticated 401; Tailscale-CLI-fails 200 with `tailscale_status: "offline"` and all other fields null.
- [x] 2.2 GREEN — `backend/app/services/tailscale_service.py` — wraps `subprocess.run(["tailscale", "status", "--json"])` + reads cert metadata from `/var/lib/tailscale/certs/<hostname>.crt` (use `cryptography` lib to parse expiry). Returns the 5-field dict. On any failure (CalledProcessError, missing file, parse error), returns `{tailscale_status: "offline", ...nulls}` — does NOT raise.
- [x] 2.3 RED — `backend/tests/test_admin_routes.py`: add `@require_admin` decorator test cases — admin proceeds, member 403, unauth 401. Test the decorator in isolation, not just `/api/admin/cert-status`.
- [x] 2.4 GREEN — `backend/app/middleware.py` — add `require_admin` decorator that combines `@require_auth` + admin-role check. Returns 403 `{"error": "admin required"}` for non-admin authenticated users.
- [x] 2.5 GREEN — `backend/app/routes/admin.py` — register blueprint `admin_bp`, mount `GET /api/admin/cert-status` using `@require_admin`. Wire blueprint in app factory.
- [x] 2.6 Run pytest — confirm all 7 new tests pass; full backend suite still green (no regression).
- [x] 2.Z Run superpowers:requesting-code-review on the diff for group 2; address CRITICAL/HIGH findings before moving on.

## 3. Frontend: AdminCertView + router + nav slot

- [x] 3.1 MOCK — open `docs/superpowers/specs/mocks/2026-05-10-nas-https-mocks.html#admin-cert-desktop`. Note the locked Notion tokens (`bg-notion-canvas`, `bg-notion-tint-mint`, `bg-notion-tint-yellow`, `bg-notion-tint-rose`, `text-notion-brand-green`, `text-notion-warning`, `text-notion-error`, `text-notion-steel`, `text-notion-charcoal`, `font-mono`) and the verbatim text strings (`证书与 Tailscale 状态`, `Tailnet 主机名`, `证书到期`, `Tailscale 连接`, `上次 renew`, `健康`, `即将到期`, `异常`, `还剩 N 天`).
- [x] 3.2 RED — `frontend/tests/views/AdminCertView.test.js`: 6 cases. Token assertions via `wrapper.classes()`:
  - Healthy state: header pill has `bg-notion-tint-mint` + `text-notion-brand-green`, days badge has `bg-notion-tint-mint`
  - Warning state (7-30d): header pill has `bg-notion-tint-yellow` + `text-notion-warning`
  - Error state (Tailscale offline): header pill has `bg-notion-tint-rose` + `text-notion-error`
  Text assertions via `wrapper.text()`:
  - Card title includes `证书与 Tailscale 状态`
  - Row labels include all 4: `Tailnet 主机名`, `证书到期`, `Tailscale 连接`, `上次 renew`
  - Status pills' verbatim text per state (`健康` / `即将到期` / `异常`)
- [x] 3.3 GREEN — `frontend/src/views/AdminCertView.vue` — fetch `GET /api/admin/cert-status` on mount + every 60s via `setInterval` (clear on unmount). Render the card per mock. Computed properties: `pillVariant` (healthy/warning/error based on Tailscale status + days_remaining bucket), `daysRemainingClass` (mint/yellow/rose).
- [x] 3.4 VISUAL DIFF — bring up dev stack (`npm run dev:up`). Mock `/api/admin/cert-status` (use Playwright route stubs or stub the store) to return healthy / warning / error in turn. Navigate to `/admin/cert` in each state; eyeball rendered UI against mock anchors `#admin-cert-desktop`, `#admin-cert-warning`, `#admin-cert-tailscale-down`. Fix any drift before the group-2 checkpoint.
- [x] 3.5 RED — `frontend/tests/router-guard.test.js`: ADD cases — admin reaches `/admin/cert` (resolves to `/admin/cert`), member redirects to `/chat`, logged-out redirects to `/login?redirect=/admin/cert`.
- [x] 3.6 GREEN — `frontend/src/router/index.js` — add route `{ path: '/admin/cert', component: AdminCertView, meta: { requiresAuth: true, requiresAdmin: true } }`. The existing admin guard (from multi-user-auth-core, redirects `/admin/*` to `/chat` for non-admin) covers this without modification.
- [x] 3.7 RED — `frontend/tests/components/AppLayout.test.js`: ADD case — when `auth.currentUser.role === 'admin'`, sidebar contains a `router-link` with `to="/admin/cert"` and visible text `证书与 Tailscale 状态`. When role is `member`, no such link exists.
- [x] 3.8 GREEN — `frontend/src/components/AppLayout.vue` — add a conditional admin nav slot (separated from regular nav by a thin divider) visible only when admin. First entry: `证书与 Tailscale 状态` → `/admin/cert`. Mobile (MeView) gets a matching link in its admin section.
- [x] 3.9 RED — `frontend/tests/views/MeView.test.js`: when admin, MeView shows a `证书与 Tailscale 状态` link going to `/admin/cert`; when member, the link is absent.
- [x] 3.10 GREEN — `frontend/src/views/MeView.vue` — add the conditional admin link in an admin section. Reuse existing styling tokens; no new tokens.
- [x] 3.11 Run vitest — all new tests pass; full suite still green.
- [x] 3.Z Run superpowers:requesting-code-review on the diff for group 3; address CRITICAL/HIGH findings before moving on.

## 4. Deployment config: docker-compose port removal + env updates

- [x] 4.1 Edit `docker-compose.prod.yml` — change `"8910:3000"` → `"127.0.0.1:8910:3000"`. This binds the host port only to the loopback interface, so Tailscale serve can still reach `localhost:8910` but the LAN cannot.

- [x] 4.2 Update NAS `.env` (UGOS file manager) — **MANUAL: do during Group 5 deploy**:
  - REMOVE `SESSION_COOKIE_SECURE=false` (let it default to `true`)
  - CHANGE `APP_BASE_URL=http://10.0.0.20:8910` → `APP_BASE_URL=https://python-agent.tail67f33e.ts.net`
  - ADD `GOOGLE_CLIENT_ID=<from task 1.7>`
  - Keep `INITIAL_ADMIN_EMAIL=austin.xyz@gmail.com` unchanged
- [x] 4.3 Update `CLAUDE.md` NAS Deployment section — added "Tailscale HTTPS" sub-section with one-time setup commands + pitfalls.
- [x] 4.Z Run superpowers:requesting-code-review on the diff for group 4 — focus on `docker-compose.prod.yml` line correctness (the `127.0.0.1:8910:3000` binding syntax) and CLAUDE.md accuracy.

## 5. Ship + smoke

- [x] 5.1 `./scripts/build-and-push.sh` — pushes new images `xuaustin/python-agent-{api,frontend}:vYYYYMMDD-<sha>` + `:latest`. (v20260516-2694f48)
- [x] 5.2 NAS UGOS Docker → python-agent project → Pull → Apply. Wait for both containers to settle.
- [x] 5.3 On NAS shell, confirm `tailscale serve status` shows the mapping `https://python-agent.<TAILNET_ID>.ts.net:443` → `http://localhost:8910`. If missing, re-run `tailscale serve --bg --https=443 http://localhost:8910`.
- [x] 5.4 In a Tailscale-connected browser: open `https://python-agent.<TAILNET_ID>.ts.net/` — should hit `/login` (redirect from `/chat` since session is invalidated). Verify green-lock TLS, no warning.
- [x] 5.5 Log in as admin (email + password). Verify redirect to `/chat`. Navigate to `/admin/cert` — should render healthy state with real values.
- [x] 5.6 Test Google Sign-In: from logout state, click Google button on LoginView (should be visible since `config.has_google` is true after `GOOGLE_CLIENT_ID` is set + HTTPS detected). Complete Google flow. Verify auto-link to existing admin row.
- [x] 5.7 Test off-LAN access: turn off device WiFi, switch to cellular. Re-open `https://python-agent.<TAILNET_ID>.ts.net/` — should still work (proves it's tailnet routing, not LAN-IP).
- [x] 5.8 Notify family: send each a Tailscale invitation link + a one-paragraph note. Help one family member through the install on a video call to confirm the flow works end-to-end.
- [x] 5.9 Confirm old URL is dead: in a browser without Tailscale connected, try `http://10.0.0.20:8910/` — should be `ERR_CONNECTION_REFUSED` (no port published to LAN anymore).
- [ ] 5.Z Run superpowers:requesting-code-review on the diff for group 5 — N/A (ops only). Skip.

## 6. Verification + close

- [x] 6.1 Run full backend pytest — 318 passed, 1 skipped (includes new tailscale_certs compose test).
- [x] 6.2 Run full frontend vitest — 220 passed (includes stale-data transient failure test).
- [x] 6.3 Run `npm run e2e:integration` against dev stack — 5 passed (multi-user-auth-core baseline preserved).
- [x] 6.4 Run superpowers:verification-before-completion: pytest green, vitest green, no `console.log` in frontend/src, no missing `user_id` filter, CLAUDE.md updated.
- [x] 6.5 Final superpowers:requesting-code-review on the entire change diff (groups 2 + 3 + 4 combined).
- [x] 6.6 Update `docs/log/2026-05-16.md` — Groups 2+3+4 documented; Group 5 deploy fields left as pending (will fill after NAS cutover).
