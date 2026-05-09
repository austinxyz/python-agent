# Multi-User Auth Requirements

**Date:** 2026-05-09
**Change name:** `multi-user-auth`
**Scope:** Replace single-user (`user_id="default"`) hardcode with proper multi-user authentication and authorization. Two coexisting login methods (email+password universal; Google Sign-In additional when HTTPS / localhost). Admin-managed allowlist via DB-backed UI.
**Status:** Requirements only. Implementation will follow as an OpenSpec change.
**UI mocks:** [mocks/2026-05-09-multi-user-auth-mocks.html](mocks/2026-05-09-multi-user-auth-mocks.html) — login flow (sidebar always visible, growing-style user pill at top, login form in main pane, default landing /chat) + mobile bottom-tab "我" 5th tab.

---

## 1. Goals

- Multiple users can use the same instance with strict per-user isolation of `private` data, `notes`, `chat_sessions`, and `chat_messages`.
- Knowledge base remains shared across all logged-in users (every user can read it; every user can ingest into it).
- Admin can invite / disable / change role of users via a UI — no `.env` editing.
- Email + password login works on **any** deployment (NAS HTTP, dev localhost, future cloud HTTPS).
- Google Sign-In works as an additional method on HTTPS / localhost. Same `users` row gets linked by email; either method authenticates the user.
- Existing `user_id="default"` data (85 files / 30 entries / 14 notes / 18 messages) is migrated cleanly to the designated initial admin (`INITIAL_ADMIN_EMAIL`) on first multi-user-aware startup.
- Backward compatibility with the current NAS deploy: shipping this change does NOT lock the user out — they can log in via email+password from day one without needing HTTPS.

## 2. Non-Goals (deferred to backlog)

- HTTPS / reverse proxy on NAS — separate change `nas-https`. Until that lands, Google login is unavailable on NAS but email+password still works.
- Cloud deployment — separate change `cloud-deploy`, depends on `nas-https` or equivalent.
- Households / multi-tenancy — separate change `households`. Allows N users to share private data within a defined household; allows multiple households on one instance.
- Member self-service registration via invite links — separate change `auth-invite-flow`. V1 admin manages everything.
- Admin review of knowledge ingestion — currently any logged-in user can ingest. Restriction is a separate change `knowledge-moderation`.
- Audit log of admin actions — separate change `auth-audit-log`.
- Password reset via email — V1 admin resets passwords manually via UI. Email-driven reset is a separate change.
- 2FA / TOTP — separate change.
- Self-service profile editing (name, avatar) — V1 reads name/picture from Google ID token only. Email+password users have no avatar.

## 3. Definitions

- **admin** — a user with `role='admin'`. Can invite/disable/delete users and manage allowlist.
- **member** — a user with `role='member'`. Can read knowledge, manage own private data, chat.
- **active** — a user with `status='active'` and either `google_sub` or `password_hash` set. Can log in.
- **invited** — a user row created by an admin but not yet activated. Has email + role + invite_token. Cannot log in until activation.
- **disabled** — `status='disabled'`. Cannot log in. Data is preserved.
- **invite token** — one-time-use random URL-safe string that lets an invited user set their initial password without admin sharing one.
- **initial admin** — the user matching `INITIAL_ADMIN_EMAIL` env var. Bootstrapped automatically on first startup. Inherits all existing `user_id="default"` data.

## 4. Data Model

### 4.1 `users` table (NEW)

```sql
CREATE TABLE users (
  id                    TEXT PRIMARY KEY,                    -- UUID v4
  email                 TEXT UNIQUE NOT NULL,                -- ALWAYS stored lowercased + trimmed (canonical identity)
  google_sub            TEXT UNIQUE,                         -- Google's stable subject claim; NULL until linked
  password_hash         TEXT,                                -- argon2id; NULL if Google-only
  name                  TEXT,                                -- display name; from Google or self-set
  picture_url           TEXT,                                -- avatar; from Google
  role                  TEXT NOT NULL DEFAULT 'member',      -- 'admin' | 'member'
  status                TEXT NOT NULL DEFAULT 'invited',     -- 'invited' | 'active' | 'disabled'
  session_version       INTEGER NOT NULL DEFAULT 1,          -- bumped on disable/password-reset to invalidate existing sessions
  invited_at            TEXT NOT NULL,
  invited_by            TEXT,                                -- FK users.id; NULL for INITIAL_ADMIN
  activated_at          TEXT,
  last_login_at         TEXT,
  password_set_at       TEXT,
  must_change_password  INTEGER NOT NULL DEFAULT 0           -- 1 = next login forces password change
);

CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_google_sub ON users(google_sub) WHERE google_sub IS NOT NULL;
CREATE INDEX idx_users_status ON users(status);
```

**Email canonicalization invariant.** Every read or write of `users.email` MUST `.strip().lower()` the input first. This applies to: bootstrap insert, admin invite, login lookup, JWT email-claim lookup, accept-invite. A user who types `Austin@Gmail.com` resolves to the same row as `austin@gmail.com`. Tests assert this round-trip explicitly.

### 4.2 `invite_tokens` table (NEW)

```sql
CREATE TABLE invite_tokens (
  token        TEXT PRIMARY KEY,                            -- 32+ char URL-safe random
  user_id      TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  expires_at   TEXT NOT NULL,                               -- 7 days after issue
  used_at      TEXT                                          -- NULL until consumed
);

CREATE INDEX idx_invite_tokens_user_id ON invite_tokens(user_id);
```

### 4.3 Existing tables — no schema change

`files`, `chat_sessions`, `chat_messages`, `notes`, `private_entries` already have `user_id` columns. The behavior change is:

- Hardcoded `user_id="default"` in routes is replaced by `g.user.id`.
- All bootstrap-migration logic operates on rows where `user_id='default'` and rewrites them to the initial admin's UUID.

## 5. Authentication

### 5.1 Email + password (universal)

Available on every deployment regardless of protocol.

**Endpoint:** `POST /api/auth/login`
- Request: `{email: string, password: string}`
- Behavior:
  - Look up user by lowercased email.
  - If not found OR `status != 'active'` OR `password_hash` is NULL → 401 `{error: "invalid credentials"}` (don't leak whether the email exists).
  - Verify `password_hash` against `password` using argon2id.
  - On match: create signed Flask session with `session['user_id'] = user.id` and `session['auth_method'] = 'password'`. Update `last_login_at`. Return `{user: {id, email, name, picture_url, role, must_change_password}}`.
  - On no match: 401.
- Rate limit: max 5 failed attempts per email per 15 minutes; further attempts return 429 regardless of correctness. (In-memory counter in V1; Redis in cloud V2.)

**Endpoint:** `POST /api/auth/change-password`
- Requires authenticated session.
- Request: `{old_password: string, new_password: string}`
- Validations: `new_password` must be ≥ 8 chars and not equal to `old_password`. `old_password` must verify (skip this check only if `must_change_password=1`, since admin-set passwords are temporary).
- On success: update `password_hash`, set `password_set_at = now`, `must_change_password = 0`. Return 200.

### 5.2 Google Sign-In (HTTPS / localhost only)

Frontend detects `window.location.protocol === 'https:' || hostname matches /^(localhost|127\.0\.0\.1)$/` and conditionally renders the GSI button. Backend endpoint is always available (rejects unverified tokens).

**Endpoint:** `POST /api/auth/login/google`
- Request: `{id_token: string}` — the JWT issued by Google's GIS button.
- Behavior:
  - Verify the JWT using `google-auth` library (signature, audience = our client ID, expiry).
  - Extract `sub`, `email`, `name`, `picture` claims.
  - Look up user by lowercased email:
    - **No row** → 403 `{error: "not invited"}`.
    - `status='disabled'` → 403 `{error: "account disabled"}`.
    - `status='invited'` AND `google_sub` is NULL → fill in `google_sub`, `name`, `picture_url`, `status='active'`, `activated_at=now`. Return 200 + user.
    - `status='active'` AND `google_sub` is NULL → fill in `google_sub`, `name`, `picture_url`. Return 200 + user. (Linking existing email+password account.)
    - `status='active'` AND `google_sub` matches → update `name`/`picture_url` from latest claims. Return 200 + user.
    - `status='active'` AND `google_sub` differs from `jwt.sub` → 403 `{error: "google account mismatch"}`. (Defends against email reuse if someone's Google account changed.)
  - On success: same Flask session as 5.1 with `session['auth_method'] = 'google'`. Update `last_login_at`.

### 5.3 Logout

**Endpoint:** `POST /api/auth/logout`
- Clears the Flask session. Returns 204.

### 5.4 Current user

**Endpoint:** `GET /api/auth/me`
- Returns 401 if no valid session.
- Returns `{user: {id, email, name, picture_url, role, must_change_password}}`.

### 5.5 Auth config (frontend bootstrap)

**Endpoint:** `GET /api/auth/config`
- Public, no auth required.
- Returns `{google_client_id: string | null, has_google: boolean}`. `google_client_id` is read from `GOOGLE_CLIENT_ID` env var; if unset, `has_google` is false and frontend hides the GSI button entirely.

### 5.6 Sessions

- Flask signed-cookie sessions using `FLASK_SECRET_KEY` (already in env).
- Cookie attributes: `HttpOnly=True`, `SameSite=Lax`. `Secure=<env-controlled>`:
  - **Default `True`** (every cookie requires HTTPS to traverse — strong security).
  - Set `SESSION_COOKIE_SECURE=false` in `.env` for NAS HTTP deployments. Cookie traverses unencrypted LAN — acceptable threat model for "single household on home wifi". This is an **explicit opt-out**, not auto-detected from `X-Forwarded-Proto` (which is easy to misconfigure when proxies aren't trustworthy).
  - Cloud deploy keeps default. Once `nas-https` lands and NAS is on HTTPS, NAS deploy flips back to default.
- Session contents on login: `session['user_id'] = user.id`, `session['session_version'] = user.session_version`, `session['auth_method'] = 'password' | 'google'`.
- Session lifetime: 30 days; `permanent=True` on login. `last_login_at` updated on every successful auth.
- **Session validation on every authenticated request:** `@require_auth` middleware loads the user by `session['user_id']`; if `user.status != 'active'` OR `user.session_version != session['session_version']` → clear cookie + 401. This is how disable / password-reset retroactively kills existing sessions despite Flask's stateless signed-cookie model: bumping `users.session_version` invalidates every cookie issued before the bump.
- No JWT, no localStorage. All auth state lives in cookies.

## 6. Authorization

### 6.1 Route guards

- `@require_auth` — applies to all routes under `/api/*` EXCEPT: `/api/auth/login`, `/api/auth/login/google`, `/api/auth/logout`, `/api/auth/me`, `/api/auth/config`, `/api/auth/accept-invite`.
- `@require_admin` — applies to all routes under `/api/admin/*`.
- After `@require_auth` resolves, `g.user` holds the User object. All queries use `g.user.id`.

### 6.2 Knowledge ingest — open to all users (V1)

Per the user's clarification (2026-05-09), the V1 model is:
- ANY authenticated user can `POST /api/ingest` regardless of role.
- The ingested file's `user_id` column records who ingested it (audit-friendly), but the chunk goes into the shared `knowledge` Qdrant collection without `user_id` filter on retrieval.
- Knowledge moderation / admin-review of ingestions is explicitly deferred (`knowledge-moderation` change).

### 6.3 Private data — strict isolation

- All `/api/private/*` routes filter by `g.user.id`.
- `/api/chat` and `/api/chat/sessions` filter by `g.user.id`.
- The `qa_agent.search_private` already enforces `user_id` filter on Qdrant — no behavior change there beyond passing `g.user.id` instead of `"default"`.

### 6.4 Admin endpoints

`/api/admin/users` — full CRUD, admin-only.

## 7. Admin user management UI

A new view at `/admin/users`, gated by `auth.user.role === 'admin'`. AppLayout adds a 5th nav item "管理" visible only to admins.

### 7.1 List users

`GET /api/admin/users` returns:
```json
[
  {
    "id": "uuid",
    "email": "...",
    "name": "...",
    "picture_url": "...",
    "role": "admin" | "member",
    "status": "invited" | "active" | "disabled",
    "has_google": bool,
    "has_password": bool,
    "invited_at": "...",
    "invited_by_email": "...",
    "activated_at": "...",
    "last_login_at": "..."
  }
]
```

### 7.2 Invite a new user

`POST /api/admin/users` body: `{email: string, role: "member" | "admin", initial_password?: string}`.
- Email is canonicalized (`.strip().lower()`) before any check.
- Validation: email format; not already in users table.
- Behavior:
  - Insert user with `status='invited'`, `password_hash=NULL`, `google_sub=NULL`.
  - Generate `invite_tokens` row with 7-day expiry.
  - If `initial_password` is provided: hash it into `password_hash`, set `must_change_password=1`. Admin-shared password is temporary; user must change on first login. The invite_token is still issued (admin can pick which to share out-of-band).
  - Return `{user, invite_url}` where `invite_url = "<base_url>/accept-invite?token=<token>"`.
  - Admin UI displays the URL with a "copy" button.

**Duplicate email handling.** If a user with the canonicalized email already exists:
- Return HTTP **409** `{error: "user already exists", existing: {id, email, status, role}}`.
- Admin UI catches the 409 and offers context-aware actions:
  - `existing.status == 'invited'` → "重新发送邀请？" (calls `POST /api/admin/users/:id/resend-invite`)
  - `existing.status == 'active'` → "用户已激活，无需重复邀请" (no destructive action)
  - `existing.status == 'disabled'` → "用户已停用，是否重新启用？" (calls `PATCH /api/admin/users/:id` with `status='active'`)

### 7.3 Update a user

`PATCH /api/admin/users/:id` body: `{role?, status?}`.
- Cannot change own role (admin can't demote themselves).
- Cannot change own status (admin can't disable themselves).
- Cannot change role of the only admin (so the last admin can't disappear).
- `status='disabled'` increments `session_version`; next request from any existing session of that user returns 401.

### 7.4 Reset password

`POST /api/admin/users/:id/reset-password` body: `{new_password?: string}`.
- If `new_password` not provided, server generates 12-char random one and returns it once in the response.
- Sets `password_hash`, `must_change_password=1`, increments `session_version` (kills existing cookies on next request).
- Use case: NAS deployment where Google login isn't available, user forgot password.

### 7.5 Resend invite

`POST /api/admin/users/:id/resend-invite`.
- Only valid for `status='invited'` users.
- Marks any existing token as used; creates new token with fresh 7-day expiry.
- Returns `{invite_url}`.

### 7.6 Delete a user

`DELETE /api/admin/users/:id`.
- Constraints: cannot delete self; cannot delete `status='active'` (admin must `disable` first to confirm intent).
- Behavior: permanently removes the user row AND all their `private_entries`, `notes`, `chat_sessions`, `chat_messages`, `files` rows. Cascades to Qdrant `private` collection (filtered delete by `user_id`). Knowledge files ingested by this user are NOT deleted (they're shared content; orphan `user_id` is acceptable for audit).

## 8. Invite acceptance flow

When an invited user opens `/accept-invite?token=<token>`:

### 8.1 Frontend `/accept-invite` route

Public route (no auth required). Reads `token` from query string.

### 8.2 Token verification

`GET /api/auth/invite/:token` (public):
- Returns `{user: {email, name?, picture_url?}, valid: bool, expired: bool}`.
- If invalid: render "邀请链接无效" page.
- If expired: render "邀请链接已过期，请向管理员申请新链接".
- If valid: render "Welcome <email>! Set your password" form.

### 8.3 Activation

`POST /api/auth/accept-invite` body: `{token, password}`.
- Validation: token exists, not used, not expired; password ≥ 8 chars.
- Behavior: set `password_hash`, `status='active'`, `activated_at=now`, mark token as used. Create Flask session.
- Returns `{user}` and redirects to `/wiki`.

### 8.4 Optional Google linking on activation

If frontend is on HTTPS / localhost, the accept-invite page can ALSO offer "或使用 Google 登录"; clicking it goes through `POST /api/auth/login/google`. Same outcome (status=active + linked).

## 9. Bootstrap migration

### 9.1 First startup detection

On every Flask app startup, run `auth_service.bootstrap_initial_admin()`:
- If `users` table is empty AND `INITIAL_ADMIN_EMAIL` env var is set:
  - Canonicalize the email (`.strip().lower()`).
  - Insert user `(email=INITIAL_ADMIN_EMAIL, role='admin', invited_by=NULL)`. Two sub-paths:
    - **If `INITIAL_ADMIN_PASSWORD` env var is also set**: hash it via argon2id, set `password_hash`, `must_change_password=1`, `status='active'`, `activated_at=now`. Admin can log in immediately with `(INITIAL_ADMIN_EMAIL, INITIAL_ADMIN_PASSWORD)` and is forced to change password on first login. **Recommended for cloud / Docker-Compose deploys** where reading container logs is awkward.
    - **If `INITIAL_ADMIN_PASSWORD` is unset**: `status='invited'`, generate invite token (7-day expiry), log the full invite URL to backend stdout (admin reads `docker logs python-agent-api` once to find it). Admin opens URL → /accept-invite → sets password → activated. **Recommended for local dev / NAS** where reading logs is trivial.
  - Run `migrate_default_user_data(initial_admin.id)`:
    - Update all rows in `files`, `chat_sessions`, `notes`, `private_entries` where `user_id='default'` to `user_id=initial_admin.id`.
    - Update Qdrant `private` collection: scroll all points; for each point with `payload.user_id='default'`, set_payload to admin's UUID. (One-time, idempotent — re-running finds 0 such points.)
  - Mark migration as done in a metadata table (or by checking that no `user_id='default'` rows remain).

### 9.2 Idempotency

- If `users` is non-empty, skip bootstrap (admin has already been created in a previous startup).
- If `user_id='default'` rows still exist after admin is created (e.g., admin was created before migration ran), still attempt the migration on next startup.

### 9.3 Failure handling

- If `INITIAL_ADMIN_EMAIL` is not set AND `users` is empty → log warning but don't crash. Bootstrap is a no-op until env var is set. Routes work in normal (non-bootstrapped) state which means: every request is unauthenticated (401), so the app is effectively dead. This is intentional — refusing to start without an admin is a footgun on Docker restarts.

## 10. Frontend changes

### 10.1 Routes

- `/login` — public — `LoginView.vue`. Email+password form always visible. GSI button conditional on host.
- `/accept-invite` — public — `AcceptInviteView.vue`. Sets initial password.
- `/change-password` — auth required — `ChangePasswordView.vue`. Required on login if `must_change_password=1`; otherwise reachable from user menu.
- `/admin/users` — admin only — `AdminUsersView.vue`. Invite, list, edit, reset password, delete.
- All existing routes (`/wiki`, `/ingest`, `/chat`, `/private`) — auth required via global router guard.

### 10.2 Router guard

```js
router.beforeEach(async (to) => {
  if (to.path === '/login' || to.path === '/accept-invite') return true
  if (!auth.currentUser) {
    await auth.fetchMe()  // hits /api/auth/me
  }
  if (!auth.currentUser) return { path: '/login', query: { redirect: to.fullPath } }
  if (to.path.startsWith('/admin/') && auth.currentUser.role !== 'admin') {
    return { path: '/wiki' }
  }
  if (auth.currentUser.must_change_password && to.path !== '/change-password') {
    return '/change-password'
  }
  return true
})
```

### 10.3 Axios 401 interceptor

```js
api.interceptors.response.use(
  (resp) => resp,
  (err) => {
    if (err.response?.status === 401) {
      auth.currentUser = null
      router.push({ path: '/login', query: { redirect: router.currentRoute.value.fullPath } })
    }
    return Promise.reject(err)
  }
)
```

### 10.4 `useAuthStore` shape

```js
state: { currentUser: null, loading: false, error: null }
actions: {
  fetchMe()             // GET /api/auth/me
  loginWithPassword(email, password)
  loginWithGoogle(idToken)
  logout()
  changePassword(oldPw, newPw)
  acceptInvite(token, password)
}
```

### 10.5 AppLayout user menu

**Desktop:** the existing AppLayout sidebar footer (where `v1.0.0` lives today) becomes a user pill: avatar (32px) + email (truncated). Clicking it opens an upward-flyout menu with the items below.

**Mobile:** the bottom-tab bar gains a 5th tab `我` (avatar image when active user has a `picture_url`, otherwise a `User` lucide icon). Tapping it opens a `/me` view that lists the same menu items in full-page mobile-friendly form. The "管理" admin entry lives inside this menu (admin role) — it is NOT a separate top-level tab. This keeps the bottom nav at exactly 5 items per iOS HIG (3-5 recommended) without making the layout admin-conditional.

Menu items (both desktop popup and mobile `/me` view):
- 修改密码 (if `password_hash` is set)
- 退出登录
- (admin only) 用户管理 — link to `/admin/users`

### 10.6 LoginView design

- Email input
- Password input (with show/hide toggle)
- "登录" button
- "—— or ——" divider
- GSI button (only shown when `auth.config.has_google && (HTTPS or localhost)`)
- Note for first-time users: "首次使用？请向管理员申请邀请链接"

## 11. Configuration (environment variables)

```bash
# Required
INITIAL_ADMIN_EMAIL=austin.xyz@gmail.com   # bootstraps the first admin
                                            # (canonicalized: .strip().lower())

# Optional — bootstrap shortcut
INITIAL_ADMIN_PASSWORD=<plaintext>          # if set, admin row created as
                                            # status='active' with hashed
                                            # password + must_change_password=1.
                                            # If unset, admin must use the invite
                                            # URL written to container logs on
                                            # first startup. Recommended for cloud.

# Optional — cookie security
SESSION_COOKIE_SECURE=false                 # default true; set false ONLY for
                                            # HTTP deploys (NAS LAN) where you
                                            # accept that session cookies traverse
                                            # unencrypted. Once nas-https lands,
                                            # remove this line.

# Optional — Google login
GOOGLE_CLIENT_ID=<oauth-client-id>          # if unset, GSI button hidden everywhere

# Already in env
FLASK_SECRET_KEY=<32-byte secret>           # signs session cookies; must be stable across restarts
```

No `AUTH_MODE` env var. Auth is always "on" — there is no single-user fallback. Email+password works everywhere; Google is opt-in (frontend self-detects HTTPS/localhost availability).

## 12. Security requirements

- Passwords hashed with argon2id, default parameters from `argon2-cffi`. No plaintext anywhere in DB or logs.
- Sessions are HttpOnly cookies signed with `FLASK_SECRET_KEY`. `Secure=True` automatically when request is HTTPS.
- Rate limit on `POST /api/auth/login` AND `POST /api/auth/login/google`: 5 fails per email per 15 min → 429. Counter is in-memory (`collections.defaultdict` keyed by lowercased email + window timestamp). Acceptable for V1 single-instance deploys; cloud / multi-instance V2 will swap in Redis. Counter resets on successful login.
- CSRF: `SameSite=Lax` on session cookie. Mutating endpoints rely on this. (Flask-WTF CSRF tokens are NOT introduced in V1 — `Lax` is sufficient for our threat model.)
- Invite tokens: 32-byte URL-safe random; expire in 7 days; one-time use.
- Admin actions (invite, role change, status change, reset password, delete) log to backend logger with admin's email + target user's email + action.
- Disabled users have all sessions invalidated by checking `users.status` on every auth-required request via `@require_auth`.

## 13. Tests

### 13.1 Backend (pytest)

- `test_auth_password_login.py`: happy path; wrong password → 401; non-existent email → 401 (same as wrong); disabled user → 401; rate limit at 5 fails → 429; **mixed-case email `Austin@Gmail.com` resolves to same user as `austin@gmail.com`**.
- `test_auth_google_login.py`: valid token + invited user → activation; valid token + active user with matching `google_sub` → login + name/picture refresh; valid token + active user with mismatched `google_sub` → 403; valid token + email not in users → 403; invalid/expired/wrong-audience token → 401; **rate limit applies to Google endpoint too (5/email/15min)**.
- `test_auth_invite_flow.py`: admin invites → token issued; user accepts → password set + activated; expired token → 410; double-use → 410.
- `test_auth_change_password.py`: must verify old; on `must_change_password=1` user, skip old verification; updates `password_set_at`.
- `test_session_invalidation.py` (NEW for session_version): user logs in (cookie has session_version=1); admin disables → next request 401; admin re-enables (session_version still 2 from disable) → original cookie still 401; user logs in fresh → new cookie works. Also: admin resets password → bumps session_version → existing cookies 401.
- `test_admin_users.py`: list, invite, role change, status change, reset password, delete; admin can't demote/disable/delete self; can't delete the only admin; **duplicate-email POST returns 409 with `existing.status` field; mixed-case duplicate detected (`Austin@Gmail.com` collides with stored `austin@gmail.com`)**.
- `test_bootstrap_migration.py`: 
  - **path A (`INITIAL_ADMIN_PASSWORD` set)**: first startup creates admin with `status='active'`, `password_hash` set, `must_change_password=1`. Admin can log in immediately with the env password. Second startup is a no-op.
  - **path B (`INITIAL_ADMIN_PASSWORD` unset)**: first startup creates admin with `status='invited'` + invite token. Token URL is logged to stdout. Second startup is a no-op (token NOT regenerated even if first invite has expired — admin uses resend-invite for that).
  - existing `user_id='default'` rows in all 4 tables get rewritten to admin UUID.
  - Qdrant `private` payload `user_id` rewritten.
  - idempotent (second run finds 0 default rows; no-op).
- `test_email_canonicalization.py` (NEW): all writes (bootstrap, invite, accept-invite) lowercase + trim; all reads canonicalize input first; `' Austin@Gmail.com '` and `'austin@gmail.com'` resolve to same row in every code path.
- `test_route_guards.py`: every existing private/chat/ingest/files/wiki route returns 401 without session; with session, scopes by `g.user.id`; session with stale `session_version` → 401 + cookie cleared.

### 13.2 Frontend (vitest)

- `LoginView.test.js`: form renders; submit calls `auth.loginWithPassword`; GSI button conditional on `auth.config.has_google` AND host.
- `AdminUsersView.test.js`: table renders users; invite form posts; role/status change buttons call correct endpoints; delete confirms before submitting; admin can't disable self UI affordance disabled.
- `auth-store.test.js`: 401 interceptor clears `currentUser` + redirects to `/login`; `fetchMe` populates store.
- `router-guard.test.js`: unauthenticated → redirect /login; member → redirect from /admin/users to /wiki; must_change_password → redirect /change-password.

### 13.3 E2E (Playwright)

- `auth.spec.ts`: login with email+password → redirected to /wiki; logout → /login. (Mocked `/api/auth/login` for deterministic tests; live one optional.)
- `admin.spec.ts`: admin sees /admin/users; invite flow; reset password.
- All existing E2E specs need a `beforeEach` that logs in with a test user, OR a global `storageState` Playwright fixture that pre-authenticates.

## 14. Migration sequence (for the implementing change)

1. Schema: add `users` and `invite_tokens` tables; idempotent migrations on startup.
2. Auth service + middleware + routes (`/api/auth/*`).
3. Replace hardcoded `user_id="default"` with `g.user.id` in all 5 route files.
4. Bootstrap migration on startup; verify on dev with seeded "default" data.
5. Frontend: useAuthStore, LoginView, router guard, axios 401 interceptor.
6. Admin UI: AdminUsersView + adminUsersStore + AppLayout 5th nav item.
7. Accept-invite + change-password views.
8. AppLayout user menu (avatar + logout).
9. Test pass: backend + frontend + E2E green.
10. Live test on local dev with two test users: invite flow, login, isolation of private data.
11. Deploy to NAS with `.env` containing:
    - `INITIAL_ADMIN_EMAIL` + `INITIAL_ADMIN_PASSWORD` (bootstrap shortcut)
    - `SESSION_COOKIE_SECURE=false` (until `nas-https` lands)
    Admin logs in with `(email, INITIAL_ADMIN_PASSWORD)` → forced to `/change-password` → sets real password → verify all 85 files / 30 entries / 14 notes / 18 messages are visible under their account. Verify a second invited member sees an empty `/private` (isolation works). Document the `SESSION_COOKIE_SECURE=false` debt in dev log so it's removed after `nas-https`.
12. Future: HTTPS change → switch to using Google login on NAS too.

## 15. Risks

- **R-01 — Bootstrap race:** if NAS restarts mid-migration, partial state could leave some `user_id='default'` rows. Mitigation: migration is idempotent (re-running finds remaining rows and processes them); `users` table check is "is admin row created" not "is migration done", so the admin row exists from the first attempt and migration retries from the second startup.
- **R-02 — Forgotten admin password on NAS:** if admin forgets password and Google login is unavailable (no HTTPS), they're locked out. Mitigation: admin can `docker exec` into the api container and run a CLI script (`python -m app.cli.reset_admin_password`) to set a new password. Documented in CLAUDE.md.
- **R-03 — Lost FLASK_SECRET_KEY:** rotating `FLASK_SECRET_KEY` invalidates all existing sessions. Acceptable; users re-login. Document in CLAUDE.md that this should be stable.
- **R-04 — Invite token interception:** a leaked URL grants the holder the ability to set a password. Mitigation: 7-day expiry; invalidation when used; admin can revoke via "resend invite" which marks old token as used.
- **R-05 — Same email on multiple Google accounts:** unlikely (Google enforces email uniqueness per account) but `google_sub` mismatch protects against linking-then-takeover.
- **R-06 — argon2 adds backend startup time:** ~50ms per login is acceptable. argon2 itself adds minimal overhead at idle.
- **R-07 — Concurrent invite to same email races UNIQUE constraint:** if two admins (or admin + script) try to invite the same email simultaneously, one INSERT wins, the other gets a 409 from §7.2's duplicate-handling logic. SQLite's UNIQUE constraint is the source of truth; no extra locking needed. Tests assert the second concurrent request gets 409 with status info, not a 500.

## 16. Acceptance criteria

The change is "done" when:

1. `INITIAL_ADMIN_EMAIL` set to your email; first login (after deploy) lands you in `/wiki` with all 85 files, 30 entries, 14 notes, 2 chat sessions visible.
2. You can invite a second user (e.g., a family member) via `/admin/users`. The invite URL works in a fresh browser; that user sets a password, logs in, sees `/wiki` (with shared knowledge) and an EMPTY `/private` page.
3. The second user creates a private entry; you (admin) cannot see it on your `/private` page.
4. Either user ingests a knowledge file; both users can see and search it.
5. You disable the second user; their next API request returns 401; their data is preserved (re-enable restores access).
6. You change your own password; old session continues; new login uses new password.
7. You sign in with Google (on localhost dev) using your admin email; the same `users` row gets `google_sub` linked; subsequent password+email login still works.
8. All Playwright + vitest + pytest suites green.

## 17. Open questions for the implementing change

(Items intentionally left unresolved until implementation; not blocking the requirements doc.)

- **Q-01 — invite email subject line and body if/when we add SMTP.** Out of V1; admin shares URL out-of-band.
- **Q-02 — username vs email-as-username.** This doc commits to email-as-identity. Future change can add `username` column if friction emerges.
- **Q-03 — session lifetime tuning.** 30 days is a guess. Watch for complaints; tune later.
- **Q-04 — admin lockout recovery on cloud (no docker exec).** Future cloud deploy needs an alternative to the CLI reset script. Maybe a "secret recovery code" printed on first admin bootstrap.
- **Q-05 — Google account email change for an active user.** Google's `sub` claim is stable but the `email` claim can change if the user renames their Gmail. Current login lookup is by email → user with stale email-to-DB mapping fails Google login with 403 "not invited". V1 workaround: admin manually updates the user's email via `PATCH /api/admin/users/:id` (endpoint NOT in V1 scope — admin can `disable + delete + re-invite` to recover). V2 may add `email` field to admin PATCH and/or fall back to `google_sub` lookup before failing. Documented as known limitation; rare in practice.

---

**Source of truth:** this document. Implementation will happen in a future OpenSpec change `multi-user-auth`. Backlog changes referenced: `nas-https`, `cloud-deploy`, `households`, `auth-invite-flow`, `knowledge-moderation`, `auth-audit-log`.
