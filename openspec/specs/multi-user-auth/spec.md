# multi-user-auth Specification

## Purpose
Replaces the hardcoded `user_id="default"` with real multi-user authentication. Multiple users log in via email+password (or Google SSI on HTTPS), with each user's private data, notes, and chat sessions fully isolated. The knowledge base remains shared. A one-time bootstrap migration rewrites all existing `user_id="default"` rows to the designated admin's UUID on first multi-user-aware startup.
## Requirements
### Requirement: Email canonicalization invariant
The system SHALL `.strip().lower()` every email at every read AND every write boundary: bootstrap insert, CLI invite, accept-invite, password login lookup, Google JWT email-claim lookup. The DB stores only canonicalized values. A user typing `Austin@Gmail.com` resolves to the same row as `austin@gmail.com`.

#### Scenario: mixed-case email writes are normalized
- **WHEN** the CLI invites `'  Austin@Gmail.com  '`
- **THEN** the row's `email` column stores `'austin@gmail.com'`

#### Scenario: mixed-case email lookup matches stored row
- **WHEN** a login form submits `email='AUSTIN@GMAIL.COM'` for a user stored as `'austin@gmail.com'`
- **THEN** the user row is found and the password check proceeds

### Requirement: Users table data model
The system SHALL define a `users` table with columns: `id` (TEXT PRIMARY KEY, UUID v4), `email` (TEXT UNIQUE NOT NULL, canonicalized per the email invariant), `google_sub` (TEXT UNIQUE, nullable), `password_hash` (TEXT, nullable, argon2id), `name` (TEXT, nullable), `picture_url` (TEXT, nullable), `role` (TEXT NOT NULL DEFAULT 'member', values 'admin' or 'member'), `status` (TEXT NOT NULL DEFAULT 'invited', values 'invited', 'active', or 'disabled'), `invited_at` (TEXT NOT NULL, ISO8601), `invited_by` (TEXT, nullable, FK users.id, NULL for bootstrap admin), `activated_at` (TEXT, nullable), `last_login_at` (TEXT, nullable). Index on `email`, partial index on `google_sub WHERE google_sub IS NOT NULL`, index on `status`. Schema migration is idempotent (`CREATE TABLE IF NOT EXISTS`).

#### Scenario: Schema migration is idempotent
- **WHEN** the app starts twice in a row against a populated DB
- **THEN** both startups complete without error and the table contents are unchanged

#### Scenario: Email is unique case-insensitively
- **WHEN** two `INSERT` statements try to store `austin@gmail.com` and `AUSTIN@GMAIL.COM` (the latter pre-canonicalization, the former already lowered)
- **THEN** the second INSERT is rejected by the UNIQUE constraint after canonicalization

### Requirement: Invite tokens table
The system SHALL define an `invite_tokens` table with columns: `token` (TEXT PRIMARY KEY, 32-byte URL-safe random), `user_id` (TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE), `expires_at` (TEXT NOT NULL, ISO8601, 7 days after issue), `used_at` (TEXT, nullable). Index on `user_id`. The token is consumed (set `used_at`) at acceptance time and never regenerated for the same user — issuing a new token marks the old one used.

#### Scenario: Token is single-use
- **WHEN** `accept-invite` is called with a token whose `used_at` is non-null
- **THEN** the response is HTTP 410 with a clear "already used" error

#### Scenario: Token expires after 7 days
- **WHEN** `accept-invite` is called with a token whose `expires_at` is in the past
- **THEN** the response is HTTP 410 with a clear "expired" error

### Requirement: Password hashing uses argon2id
The system SHALL hash all passwords with argon2id via `argon2-cffi` library defaults. Plaintext passwords MUST NOT appear in the database, in any logger output, or in any HTTP response body. `password_hash` is NULL for users who haven't set a password yet (e.g., during the `invited` state before they accept the invite).

#### Scenario: Plaintext password never logged
- **WHEN** a login request is processed with logging at DEBUG level
- **THEN** the request body's `password` field is redacted in logs

#### Scenario: Password verify uses argon2id
- **WHEN** a user is created with `password='hello123'` then logs in with `password='hello123'`
- **THEN** the stored `password_hash` starts with `$argon2id$` and `verify()` returns true

### Requirement: POST /api/auth/login (email + password)
The endpoint SHALL accept `{email: string, password: string}` and return either `{user: {id, email, name, picture_url, role}}` with a Flask session cookie (HTTP 200) or HTTP 401 with `{error: "invalid credentials"}`. The 401 response is identical for: nonexistent email, wrong password, status != 'active', `password_hash` is NULL — preventing email-existence enumeration. On success, `last_login_at` is updated.

#### Scenario: Successful password login sets session
- **WHEN** an active user with `password_hash` set submits correct credentials
- **THEN** the response is 200 with `{user: ...}` and the response sets a `session` cookie

#### Scenario: Wrong password returns 401 with same error as missing user
- **WHEN** any of: email not in users, status != 'active', wrong password, no password_hash
- **THEN** the response is HTTP 401 with body `{error: "invalid credentials"}` (no further detail)

#### Scenario: Disabled user cannot log in
- **WHEN** a user with `status='disabled'` submits correct credentials
- **THEN** the response is HTTP 401 with `{error: "invalid credentials"}` (not "disabled" — same as wrong password)

### Requirement: POST /api/auth/login/google (Google ID token)
The endpoint SHALL accept `{id_token: string}`, verify the JWT using `google-auth` (signature, audience matches `GOOGLE_CLIENT_ID`, expiry valid), extract `sub`, `email`, `name`, `picture` claims, then look up by canonicalized email. Behavior depends on user state and `google_sub` linkage:

| Existing user state | google_sub | Action |
|--|--|--|
| Not in users | — | 403 `{error: "not invited"}` |
| `status='disabled'` | any | 403 `{error: "account disabled"}` |
| `status='invited'`, `google_sub IS NULL` | — | Activate: set `google_sub`, `name`, `picture_url`, `status='active'`, `activated_at=now`. 200 + session. |
| `status='active'`, `google_sub IS NULL` | — | Link: set `google_sub`, refresh `name`/`picture_url`. 200 + session. |
| `status='active'`, `google_sub` matches `jwt.sub` | match | Refresh `name`/`picture_url` from claims. 200 + session. |
| `status='active'`, `google_sub` differs from `jwt.sub` | mismatch | 403 `{error: "google account mismatch"}` |

Invalid / expired / wrong-audience tokens return HTTP 401.

#### Scenario: Invited user activated by Google login
- **WHEN** a user row exists with `status='invited'`, `google_sub IS NULL`, email `wife@gmail.com`, and a valid Google JWT for that email is submitted
- **THEN** the row is updated to `status='active'`, `google_sub` set from JWT, response is 200 with session cookie

#### Scenario: Sub mismatch returns 403
- **WHEN** a user row has `google_sub='X'` and a JWT arrives with same email but `sub='Y'`
- **THEN** the response is HTTP 403 with `{error: "google account mismatch"}`

### Requirement: POST /api/auth/logout
The endpoint SHALL clear the Flask session and return HTTP 204. No request body is required. Subsequent requests with the now-stale cookie return 401 from `@require_auth`.

#### Scenario: Logout clears session
- **WHEN** an authenticated user calls POST /api/auth/logout
- **THEN** response is 204 and the next call to GET /api/auth/me returns 401

### Requirement: GET /api/auth/me
The endpoint SHALL return `{user: {id, email, name, picture_url, role}}` for an authenticated session, or HTTP 401 if no valid session.

#### Scenario: Returns current user on authenticated session
- **WHEN** an active user calls GET /api/auth/me with a valid session cookie
- **THEN** response is 200 with their user object

#### Scenario: Disabled user gets 401
- **WHEN** a user whose status was changed to 'disabled' since their session was created calls GET /api/auth/me
- **THEN** response is 401 (per-request status check), session cookie is cleared

### Requirement: GET /api/auth/config (public)
The endpoint SHALL return `{has_google: bool, google_client_id: string | null}` without requiring authentication. `has_google` is true iff `GOOGLE_CLIENT_ID` env var is non-empty. Frontend uses this to decide whether to render the GSI button.

#### Scenario: Config exposes Google client id when present
- **WHEN** GOOGLE_CLIENT_ID is set in env and config endpoint is hit
- **THEN** response is 200 with `{has_google: true, google_client_id: "<env value>"}`

#### Scenario: Config hides Google when env unset
- **WHEN** GOOGLE_CLIENT_ID is empty or unset
- **THEN** response is 200 with `{has_google: false, google_client_id: null}`

### Requirement: GET /api/auth/invite/<token> (public)
The endpoint SHALL accept an invite token in the URL path and return `{user: {email, name, picture_url}, valid: bool, expired: bool}`. `valid=true` requires the token to exist, be unused, and not be expired. The endpoint deliberately returns enough info for the frontend to render a "Hi <email>, <inviter> invited you" welcome banner — including the inviter's basic info.

#### Scenario: Valid token returns user + inviter context
- **WHEN** a valid unused unexpired token is queried
- **THEN** response is `{user: {email, name, picture_url}, valid: true, expired: false}` plus inviter context for the welcome banner

#### Scenario: Expired token reports expired
- **WHEN** a token whose `expires_at` is in the past is queried
- **THEN** response is `{user: ..., valid: false, expired: true}`

### Requirement: POST /api/auth/accept-invite
The endpoint SHALL accept `{token: string, password: string}`, validate the token (exists, unused, unexpired) and the password (≥ 8 chars), then activate the user atomically: set `password_hash`, `status='active'`, `activated_at=now`, mark token used, open Flask session, return `{user}`. On any failure, return appropriate 4xx with no partial state.

#### Scenario: Successful invite acceptance activates user and signs in
- **WHEN** valid token + password ≥ 8 chars submitted
- **THEN** user row updates to status='active', token's used_at set, session created; response is 200 with user object

#### Scenario: Password too short rejected
- **WHEN** valid token + password < 8 chars submitted
- **THEN** response is HTTP 400 with `{error: "password must be at least 8 characters"}` and no DB write

#### Scenario: Already-used token rejected
- **WHEN** the token has `used_at` set
- **THEN** response is HTTP 410 with `{error: "invite already used"}`

### Requirement: POST /api/auth/change-password
The endpoint SHALL require authenticated session, accept `{old_password: string, new_password: string}`, verify `old_password` against the stored hash, validate `new_password` (≥ 8 chars, different from old), and update `password_hash`. Returns HTTP 200 on success or 400 / 401 on failure.

#### Scenario: Successful password change
- **WHEN** an authenticated user submits correct old + new (different, ≥ 8 chars)
- **THEN** response is 200 and subsequent logins use the new password

#### Scenario: Wrong old password rejected
- **WHEN** authenticated user submits wrong old_password
- **THEN** response is HTTP 401 with `{error: "old password incorrect"}`

#### Scenario: Same-as-old new password rejected
- **WHEN** new_password equals old_password
- **THEN** response is HTTP 400 with `{error: "new password must differ from old"}`

### Requirement: @require_auth middleware enforces authenticated active sessions
The system SHALL implement a `@require_auth` decorator that, on each request: (a) reads `session['user_id']`, (b) loads the user row, (c) asserts `status='active'`, (d) on any failure clears the session cookie and returns HTTP 401. On success, sets `g.user` to the user object so route handlers can use `g.user.id`. Applied to every `/api/*` route EXCEPT: `POST /api/auth/login`, `POST /api/auth/login/google`, `POST /api/auth/logout`, `GET /api/auth/me` (which has its own short-circuit), `GET /api/auth/config`, `GET /api/auth/invite/<token>`, `POST /api/auth/accept-invite`.

#### Scenario: Unauthenticated request to protected endpoint returns 401
- **WHEN** a request with no session cookie hits `GET /api/private/entries`
- **THEN** response is 401, no DB queries are made for entries

#### Scenario: Disabled user request returns 401 even with valid cookie
- **WHEN** a user whose status changed to 'disabled' (after their cookie was issued) hits any protected endpoint
- **THEN** response is 401, cookie is cleared

#### Scenario: g.user.id replaces hardcoded "default"
- **WHEN** an authenticated request reaches a handler in files.py / private.py / chat.py / ingest.py / wiki.py
- **THEN** the handler uses `g.user.id` for any per-user filtering or insertion (NOT the literal `"default"`)

### Requirement: Bootstrap migration on first startup
On every app startup, the system SHALL run `bootstrap_initial_admin()`. If `users` is empty AND `INITIAL_ADMIN_EMAIL` env var is set: insert the admin row (`role='admin'`, `status='invited'`, `invited_by=NULL`); generate an invite token (7-day expiry); log the full invite URL to stdout (one line, prefixed `[BOOTSTRAP] Admin invite URL: ...`). Then run `migrate_default_user_data(admin.id)` which UPDATEs all `files`, `chat_sessions`, `notes`, `private_entries` rows where `user_id='default'` to the admin's UUID, AND scrolls Qdrant `private` collection rewriting any payload `user_id='default'` to the admin's UUID. Idempotent: subsequent startups (with non-empty users) skip the bootstrap entirely; if bootstrap completes but migration is interrupted, the next startup retries the migration.

#### Scenario: First startup with INITIAL_ADMIN_EMAIL set and existing default data
- **WHEN** the app starts with empty users table, `INITIAL_ADMIN_EMAIL=austin.xyz@gmail.com` set, and 85 files / 30 entries / etc. with `user_id='default'`
- **THEN** users table has 1 row (admin), invite_tokens has 1 row, all 85+30+14+18 rows now have `user_id=<admin UUID>`, Qdrant private payloads similarly rewritten, and stdout contains the invite URL line

#### Scenario: Second startup is a no-op
- **WHEN** the app starts after a successful bootstrap (users table non-empty)
- **THEN** no admin row is created, no invite URL is logged, no SQL UPDATE is executed

#### Scenario: Missing INITIAL_ADMIN_EMAIL with empty users does not crash
- **WHEN** the app starts with empty users table and `INITIAL_ADMIN_EMAIL` unset
- **THEN** the app starts successfully, logs a warning, and every authenticated endpoint returns 401 (no admin to log in as)

### Requirement: CLI invite command
The system SHALL provide `python -m app.cli.invite_user <email> [role]` invokable inside the api container via `docker exec`. Default role is `member`. The command performs the same logic as the future `POST /api/admin/users` endpoint: canonicalize email, verify uniqueness (409 / non-zero exit + clear error message if collision), insert user row + invite token, print the invite URL to stdout for the admin to copy.

#### Scenario: CLI invite generates URL and DB rows
- **WHEN** `docker exec -it api python -m app.cli.invite_user wife@gmail.com member` is run
- **THEN** users table gains a row with status='invited', invite_tokens has a corresponding token, stdout has one line of the form `Invite URL: http://<host>/accept-invite?token=<token>`

#### Scenario: CLI invite for existing email reports clearly
- **WHEN** `python -m app.cli.invite_user austin.xyz@gmail.com member` is run while admin already has `status='active'`
- **THEN** exit code is non-zero, stderr explains "user already exists with status=active", DB unchanged

### Requirement: Session cookie security via SESSION_COOKIE_SECURE env var
The system SHALL read `SESSION_COOKIE_SECURE` env var (default `true`) and set Flask's `SESSION_COOKIE_SECURE` config accordingly. After `nas-https` lands, NAS deploys use the default `true` (HTTPS-only cookies). Local dev on `localhost` may set `SESSION_COOKIE_SECURE=false` since browsers treat `localhost` as a "secure context" for many purposes but still require the `Secure` attribute to be absent for plain HTTP. `SameSite=Lax` and `HttpOnly=True` are always set regardless of `Secure`.

#### Scenario: Cookie has Secure attribute when env var unset
- **WHEN** `SESSION_COOKIE_SECURE` env var is unset and a login response is sent
- **THEN** the `Set-Cookie` header includes `Secure`, `HttpOnly`, and `SameSite=Lax` attributes

#### Scenario: Cookie omits Secure when env var is "false"
- **WHEN** `SESSION_COOKIE_SECURE=false` and a login response is sent
- **THEN** the `Set-Cookie` header includes `HttpOnly` and `SameSite=Lax` but NOT `Secure`

#### Scenario: NAS deploy uses Secure cookie after nas-https lands
- **WHEN** the NAS `.env` no longer sets `SESSION_COOKIE_SECURE` (the line is removed) and a login response is sent over HTTPS
- **THEN** the `Set-Cookie` header includes `Secure` and the cookie is rejected by browsers if the request was over plain HTTP (which the tailnet entry no longer permits)

### Requirement: Admin role gates admin-only API endpoints
The system SHALL provide a `@require_admin` decorator (or equivalent) that combines `@require_auth` with an additional `g.user.role === 'admin'` check. Routes under `/api/admin/*` SHALL use this decorator. Non-admin authenticated users receive HTTP 403 `{"error": "admin required"}`. Unauthenticated requests receive HTTP 401 via the underlying `@require_auth`.

#### Scenario: Admin-only endpoint accepts admin
- **WHEN** an admin-authenticated request hits any `/api/admin/*` endpoint that uses `@require_admin`
- **THEN** the request proceeds to the handler and returns HTTP 200 (or whatever the handler specifies)

#### Scenario: Admin-only endpoint rejects member
- **WHEN** a member-authenticated request hits any `/api/admin/*` endpoint
- **THEN** the response is HTTP 403 with body `{"error": "admin required"}` and the handler is NOT invoked

#### Scenario: Admin-only endpoint rejects unauthenticated
- **WHEN** an unauthenticated request hits any `/api/admin/*` endpoint
- **THEN** the response is HTTP 401 (standard `@require_auth` behavior) and the admin-check is NOT reached

### Requirement: @require_admin middleware extends @require_auth
The system SHALL provide a `@require_admin` decorator that first runs the `@require_auth` middleware (loads user, asserts active status, sets `g.user`), then asserts `g.user.role == 'admin'`. On failure: 401 if not authenticated (cookie cleared); 403 if authenticated but not admin (cookie preserved). The 401 vs 403 distinction matters because the frontend's axios 401 interceptor redirects to /login, while 403 should NOT redirect (just show "permission denied").

#### Scenario: Unauthenticated request to admin endpoint returns 401
- **WHEN** an unauthenticated request hits `GET /api/admin/users`
- **THEN** response is 401 and the Set-Cookie header clears any stale session

#### Scenario: Authenticated member request to admin endpoint returns 403
- **WHEN** a `role='member'` user with valid session hits `GET /api/admin/users`
- **THEN** response is 403 with `{error: "admin access required"}`, cookie preserved

#### Scenario: Admin request proceeds normally
- **WHEN** a `role='admin'` user with valid session hits `GET /api/admin/users`
- **THEN** response is 200 with the user list

### Requirement: GET /api/admin/users (admin-only)
The endpoint SHALL return all users sorted by `invited_at DESC`. Response shape per user: `{id, email, name, picture_url, role, status, has_google: bool, has_password: bool, invited_at, invited_by_email, activated_at, last_login_at}`. `invited_by_email` is the email of the user referenced by `invited_by` (NULL for the bootstrap admin). `has_google = google_sub IS NOT NULL`; `has_password = password_hash IS NOT NULL`.

#### Scenario: Returns all users with computed fields
- **WHEN** an admin calls GET /api/admin/users with 4 users in DB
- **THEN** response is 200 with array of 4 entries, each containing the spec'd fields, sorted newest-invitation-first

#### Scenario: invited_by_email is null for bootstrap admin
- **WHEN** the bootstrap admin row (with `invited_by=NULL`) is in the result
- **THEN** that entry has `invited_by_email: null`

### Requirement: POST /api/admin/users (admin-only)
The endpoint SHALL accept `{email: string, role: "admin" | "member"}`. Behavior:
1. Canonicalize email (`.strip().lower()`).
2. If email already in users → return **409** + `{error: "user already exists", existing: {id, email, status, role}}`.
3. Otherwise: insert user row (`status='invited'`, `invited_by=g.user.id`); generate invite_tokens row (7-day expiry); return **201** + `{user: <full user object>, invite_url: "<base>/accept-invite?token=<token>"}`.

`<base>` is derived from `request.host_url` so the URL works regardless of which origin the admin is on.

#### Scenario: New email creates user + invite token
- **WHEN** admin POSTs `{email: "wife@gmail.com", role: "member"}` to a clean DB
- **THEN** response is 201 with `{user, invite_url}`, users table has the new row with `status='invited'`, invite_tokens has the corresponding token

#### Scenario: Duplicate email returns 409 with existing-state context
- **WHEN** admin POSTs an email that already exists with `status='active'`, `role='member'`
- **THEN** response is 409 with `{error: "user already exists", existing: {id, email, status: "active", role: "member"}}`, no DB write

#### Scenario: Email is canonicalized before duplicate check
- **WHEN** admin POSTs `email='AUSTIN@GMAIL.COM'` and a row exists with `email='austin@gmail.com'`
- **THEN** response is 409 (collision detected on canonical form)

### Requirement: PATCH /api/admin/users/:id (admin-only)
The endpoint SHALL accept partial body `{role?, status?}` and apply changes. Self-protection rules (HTTP 400 on violation):
- Cannot change own role (admin cannot demote self).
- Cannot change own status to anything other than `'active'`.
- Cannot demote `'admin'` → `'member'` if the target is the only admin (server-side count check).
- Cannot set `status` to a value outside the enum (`'invited'`, `'active'`, `'disabled'`).

On valid mutation: update the row, return 200 + the updated user object.

#### Scenario: Demote a non-self member (no-op since it's already member, just illustrative)
- **WHEN** admin PATCHes a different admin user with `{role: "member"}` (and at least one other admin remains)
- **THEN** response is 200 with the updated user

#### Scenario: Cannot demote self
- **WHEN** admin PATCHes their own id with `{role: "member"}`
- **THEN** response is 400 with `{error: "cannot change own role"}`

#### Scenario: Cannot demote the only admin
- **WHEN** admin PATCHes the only admin user (whether self or another) with `{role: "member"}` while no other admins exist
- **THEN** response is 400 with `{error: "cannot demote the only admin"}`

#### Scenario: Cannot disable self
- **WHEN** admin PATCHes their own id with `{status: "disabled"}`
- **THEN** response is 400 with `{error: "cannot disable self"}`

#### Scenario: Disable propagates: target's next request returns 401
- **WHEN** admin disables a user → that user's existing session attempts any `/api/private/...` request
- **THEN** the request returns 401 (per-request status check from core's `@require_auth`)

### Requirement: DELETE /api/admin/users/:id (admin-only)
The endpoint SHALL permanently delete the user row AND cascade-delete:
1. All rows in `private_entries`, `notes`, `chat_sessions`, `chat_messages` (the latter via cascade from `chat_sessions`) where `user_id = :id`.
2. Qdrant filter-delete on `private` collection by `user_id = :id`.
3. The `users` row itself.

Self-protection (400):
- Cannot delete self.
- Cannot delete a user with `status='active'` (must `disable` first; admin disables to confirm intent).
- Cannot delete the only admin (covers self via "cannot delete self" but also catches other-admin-deleting-only-admin edge case).

Files in the shared `knowledge` collection ingested by this user are NOT deleted — knowledge is shared content; the orphan `user_id` is acceptable for audit.

The Qdrant filter-delete SHALL run BEFORE the SQLite delete so that, on partial failure, the recovery state is "vectors gone, SQLite row still there" (admin can retry the SQLite delete) rather than "vectors orphaned, SQLite row gone" (unrecoverable without manual cleanup).

#### Scenario: Delete cascades private + chat data, preserves knowledge files
- **WHEN** admin deletes a user with: 5 private entries, 3 notes, 2 chat sessions (with 8 messages), 4 ingested knowledge files
- **THEN** post-delete: users row gone, 5+3+2+8 rows gone from respective tables, Qdrant private collection has 0 points with that user_id, files table still has 4 rows with the orphan user_id

#### Scenario: Cannot delete active user
- **WHEN** admin DELETEs a user with `status='active'`
- **THEN** response is 400 with `{error: "user must be disabled before deletion"}`, no data changes

#### Scenario: Cannot delete self
- **WHEN** admin DELETEs their own id
- **THEN** response is 400 with `{error: "cannot delete self"}`

#### Scenario: Qdrant before SQLite ordering
- **WHEN** the SQLite delete is mocked to fail after the Qdrant filter-delete succeeds
- **THEN** the failure response is 500 AND the user's row is still in users (recoverable: retry the DELETE)

### Requirement: POST /api/admin/users/:id/resend-invite (admin-only)
The endpoint SHALL only succeed when target user has `status='invited'`. Marks any existing `invite_tokens` row for that user as used (`used_at = now`); creates a fresh token row with new expiry. Returns 200 + `{invite_url}`. If `status != 'invited'`, returns 400 + `{error: "user is not in invited state"}`.

#### Scenario: Resend invite generates new token, invalidates old
- **WHEN** admin resends invite for a user with `status='invited'` and an existing unused token
- **THEN** response is 200 with new invite_url; the old token now has `used_at` set; a new token row exists with fresh `expires_at`

#### Scenario: Resend invite for active user is rejected
- **WHEN** admin POSTs resend-invite for a user with `status='active'`
- **THEN** response is 400 with `{error: "user is not in invited state"}`, no token changes

