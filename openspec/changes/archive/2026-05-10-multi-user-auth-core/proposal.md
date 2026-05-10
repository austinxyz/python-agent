## Why

Today every backend route hardcodes `user_id="default"` (`backend/app/routes/files.py:11`, `ingest.py:50`, etc.). The schema is multi-user-ready (every table has a `user_id` column, every Qdrant `private` query enforces a `user_id` filter), but no actual authentication exists. NAS is now the canonical instance — adding family / friends as users requires login, per-user data isolation, and a way to bootstrap each new person.

This is the **first half** of the multi-user split. Backend auth, the user data model, and the user-facing login / invite / password flows ship here. Admin user-management UI ships in a follow-up `multi-user-auth-admin-ui` change. During this change's lifetime, admin invites use a CLI command (`docker exec ... python -m app.cli.invite_user ...`) — acceptable interim because the user is the only admin and inviting is rare.

Source of truth for design: [docs/superpowers/specs/2026-05-09-multi-user-auth-requirements.md](../../../docs/superpowers/specs/2026-05-09-multi-user-auth-requirements.md). UI mocks: [docs/superpowers/specs/mocks/2026-05-09-multi-user-auth-mocks.html](../../../docs/superpowers/specs/mocks/2026-05-09-multi-user-auth-mocks.html). The 7 hardening items deferred per the 2026-05-09 slim discussion (rate limiting on login endpoints, `session_version` invalidation, `INITIAL_ADMIN_PASSWORD` shortcut, `must_change_password` flow, admin reset-password endpoint, admin operation audit logging, concurrent-invite race tests) are **out of scope** here and will be addressed in a future hardening change.

## What Changes

### Data model
- **NEW `users` table:** `id` (UUID) / `email` (UNIQUE, lowercased + trimmed on every read & write) / `google_sub` (UNIQUE, NULL until first Google login) / `password_hash` (argon2id, NULL if Google-only) / `name` / `picture_url` / `role` (`'admin'` | `'member'`, default `'member'`) / `status` (`'invited'` | `'active'` | `'disabled'`, default `'invited'`) / `invited_at` / `invited_by` (FK users.id, NULL for bootstrap) / `activated_at` / `last_login_at`.
- **NEW `invite_tokens` table:** `token` (TEXT PRIMARY KEY, 32-byte URL-safe random) / `user_id` (FK users.id, ON DELETE CASCADE) / `expires_at` (7 days from issue) / `used_at` (NULL until consumed).
- **No `session_version`, no `must_change_password`, no `password_set_at`** — these were in the v2 requirements but dropped in the slim. Disabled-user enforcement uses a per-request `users.status='active'` check in middleware (acceptable for V1 family scale; full session revocation lands in the hardening change).

### Backend services & middleware
- **NEW `auth_service`:** argon2id password hash/verify, Google ID-token verification via `google-auth`, email canonicalization helper, current-user resolution for routes.
- **NEW `user_service`:** users + invite_tokens CRUD, bootstrap-from-INITIAL_ADMIN_EMAIL, `migrate_default_user_data(admin_id)` that rewrites `user_id='default'` rows in `files`/`chat_sessions`/`notes`/`private_entries` plus Qdrant `private` payloads to the admin's UUID. Idempotent.
- **NEW `@require_auth` middleware:** loads user from `session['user_id']`, asserts `status='active'`, exposes `g.user`. On any failure: clear cookie + 401. Applied to every route under `/api/*` except auth endpoints listed below.

### Backend routes (NEW under `/api/auth/`)
- `POST /api/auth/login` — body `{email, password}`. 401 on any failure (no enumeration leak).
- `POST /api/auth/login/google` — body `{id_token}`. Verifies via Google's library. Looks up by canonicalized email → activates `invited` users / refreshes `name`+`picture_url` for `active` users / 403 on mismatch or unknown email / 403 on disabled.
- `POST /api/auth/logout` — clears Flask session. 204.
- `GET /api/auth/me` — returns `{user}` or 401.
- `GET /api/auth/config` — public. Returns `{has_google: bool, google_client_id: string|null}` so frontend knows whether to render the GSI button.
- `GET /api/auth/invite/<token>` — public. Returns `{user: {email, name?, picture_url?}, valid, expired}` so the accept-invite page can render context before the user types a password.
- `POST /api/auth/accept-invite` — body `{token, password}` (password ≥ 8 chars). Activates the invited user, hashes the password, marks token used, opens session, returns `{user}`.
- `POST /api/auth/change-password` — auth required. Body `{old_password, new_password}` (new ≥ 8 chars, different from old). Verifies old, swaps hash. **No session invalidation in V1** (the password change just lets future logins use the new password; existing cookies stay valid until expiry — hardening change adds revocation).

### Backend routes (MODIFIED)
- Every route in `files.py`, `ingest.py`, `chat.py`, `private.py`, `wiki.py` adds `@require_auth` and replaces `user_id="default"` with `g.user.id`. Same scoping logic, real identity. No new endpoints; no schema migrations on those tables.

### Bootstrap (idempotent on every startup)
- If `users` is empty AND `INITIAL_ADMIN_EMAIL` is set: insert admin row (`role='admin'`, `status='invited'`, `invited_by=NULL`); generate invite token; **log the full invite URL to stdout** (`docker logs python-agent-api`) so the admin can find it. Then run `migrate_default_user_data(admin.id)`.
- Idempotent: if `users` is non-empty, skip; if any `user_id='default'` rows remain (admin row exists but migration was interrupted), retry the data migration.
- If `INITIAL_ADMIN_EMAIL` is unset AND `users` is empty: log warning, no crash. Every authenticated request returns 401 (effectively dead) until env var is set + container restarted. **Intentional footgun protection** — refusing to start with no admin would break Docker restart loops on misconfig.

### CLI tool (interim until admin-ui change)
- **NEW `python -m app.cli.invite_user <email> [role]`** — admin runs via `docker exec`. Validates email, creates user row + invite token, prints invite URL to stdout. Same logic as the `multi-user-auth-admin-ui` change's HTTP endpoint will use later, just minus the wrapping route.

### Frontend
- **NEW `LoginView.vue`** at `/login`: email + password form, "登录" CTA. Below: 分隔线 "或" + Google Sign-In button **conditional on `auth.config.has_google && (HTTPS || hostname matches localhost)`**. Below: small grey hint "没账号？请管理员发邀请链接".
- **NEW `AcceptInviteView.vue`** at `/accept-invite?token=...`: reads token; calls `GET /api/auth/invite/:token`; renders welcome banner with inviter's name + avatar, locked email field, password + confirm fields, plus optional Google linking when HTTPS. Three error states (expired / used / invalid) per the mocks.
- **NEW `ChangePasswordView.vue`** at `/change-password`: 3 fields (old / new / confirm); calls `POST /api/auth/change-password`.
- **NEW `MeView.vue`** at `/me` (mobile only): full-page user menu — avatar card + 修改密码 link + 退出登录 button. Routed when 5th bottom-tab "我" is tapped.
- **NEW `useAuthStore`:** `currentUser`, `config` (auth config), `loading`, `error`. Actions: `fetchMe`, `fetchConfig`, `loginWithPassword`, `loginWithGoogle`, `acceptInvite`, `changePassword`, `logout`. On any 401 from any axios call, store clears `currentUser` and router pushes `/login`.
- **MODIFIED `AppLayout.vue`:**
  - Sidebar (desktop md+) gains a **user pill at the top** (above logo, growing-style). Logged-out: gray avatar + "未登录" + 紫色【登录】button. Logged-in: avatar (Google picture if present, else first letter colored by hash of email) + name + role badge + email truncated + ⏻ logout icon. Both states are 56px tall.
  - Bottom-tab (mobile md-) gains a **5th tab "我"** that opens `/me`. The "管理" admin-only nav item is NOT in this change (it lands with `multi-user-auth-admin-ui`).
- **MODIFIED `router/index.js`:**
  - Adds `/login`, `/accept-invite`, `/change-password`, `/me` routes.
  - Global `beforeEach` guard: public paths = `/login`, `/accept-invite`; everything else requires `auth.currentUser`. Unauthenticated → push `/login?redirect=<original>`. After login, redirect honors `?redirect` if present, else `/chat` (changed from current `/wiki`).
- **MODIFIED `api/index.js`:** axios response interceptor — on 401, clears `auth.currentUser` and pushes `/login`.

### Configuration
- **NEW env vars** in `.env`:
  - `INITIAL_ADMIN_EMAIL=austin.xyz@gmail.com` (required for bootstrap on first deploy)
  - `GOOGLE_CLIENT_ID=<oauth-client-id>` (optional; if unset GSI button hidden everywhere)
  - `SESSION_COOKIE_SECURE=false` (default true in code; set false explicitly for NAS HTTP deployment until `nas-https` lands)
- **NEW backend deps** in `requirements.txt`: `argon2-cffi>=23.0`, `google-auth>=2.0`.

## Capabilities

### New Capabilities

- `multi-user-auth`: identity, sessions, invite flow, bootstrap, password management. Both this change and the follow-up admin-UI change will add requirements here.

### Modified Capabilities

- `frontend-scaffold`: AppLayout adds the user pill at sidebar top + mobile 5th tab "我"; router gains the auth guard + new routes (`/login`, `/accept-invite`, `/change-password`, `/me`); axios gains the 401 interceptor; default landing changes from `/wiki` to `/chat`.

## Impact

- **Files added (backend):** `backend/app/services/auth_service.py`, `backend/app/services/user_service.py`, `backend/app/middleware.py`, `backend/app/routes/auth.py`, `backend/app/cli/invite_user.py`. `backend/db/schema.sql` gets `users` + `invite_tokens` tables + indexes.
- **Files added (frontend):** `frontend/src/views/LoginView.vue`, `AcceptInviteView.vue`, `ChangePasswordView.vue`, `MeView.vue`; `frontend/src/stores/auth.js`.
- **Files modified (backend):** `files.py`, `ingest.py`, `chat.py`, `private.py`, `wiki.py` — `@require_auth` decorator + `g.user.id` substitution. `requirements.txt` (+2 deps).
- **Files modified (frontend):** `AppLayout.vue` (user pill + logout flow + 5th mobile tab), `router/index.js` (auth guard + new routes), `api/index.js` (401 interceptor), default route changes from `/wiki` to `/chat`.
- **Files modified (config + docs):** `.env.example` (new vars), `CLAUDE.md` (Deployment section + new Pitfall: "remember `SESSION_COOKIE_SECURE=false` on NAS HTTP until nas-https"; new Pitfall: "use `python -m app.cli.invite_user` to invite users until admin UI ships").
- **External dependencies (new):** Docker Hub image rebuilt and pushed; NAS deploy needs `.env` updated with `INITIAL_ADMIN_EMAIL` + `SESSION_COOKIE_SECURE=false`.
- **Operational:** existing user data migrated transparently to bootstrap admin's UUID — no manual step. Admin invites family members via `docker exec ... python -m app.cli.invite_user wife@gmail.com member`, copies the URL printed to stdout, sends via 微信. Family member sets password, lands at `/chat`, sees empty `/private` (isolation works). NAS deploy on HTTP keeps working because of `SESSION_COOKIE_SECURE=false`.
- **Out of scope** (deferred to backlog):
  - Rate limiting on login endpoints (`auth-rate-limiting` change)
  - `session_version` invalidation (current V1 enforces disabled status on each request only)
  - `INITIAL_ADMIN_PASSWORD` shortcut, `must_change_password` flow (added if/when admin UI grows ability to set initial passwords)
  - Admin reset-password endpoint (member self-recovery via Google login if available; otherwise admin disable+reinvite for now)
  - Admin operation audit logging (`auth-audit-log` change)
  - AdminUsersView UI (`multi-user-auth-admin-ui` change — see split note in requirements doc)
  - HTTPS / reverse proxy on NAS (`nas-https` change)
  - Cloud deployment (`cloud-deploy` change, depends on `nas-https`)
  - Households / multi-tenancy (`households` change)

Backlog changes referenced: `multi-user-auth-admin-ui`, `nas-https`, `cloud-deploy`, `households`, `auth-invite-flow`, `knowledge-moderation`, `auth-audit-log`, `auth-rate-limiting`.
