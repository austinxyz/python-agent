## ADDED Requirements

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
The system SHALL read `SESSION_COOKIE_SECURE` env var (default `true`) and set Flask's `SESSION_COOKIE_SECURE` config accordingly. NAS HTTP deployments set `SESSION_COOKIE_SECURE=false`; this is documented in CLAUDE.md as temporary debt that gets removed when `nas-https` lands. `SameSite=Lax` and `HttpOnly=True` are always set regardless of `Secure`.

#### Scenario: Cookie has Secure attribute when env var unset
- **WHEN** `SESSION_COOKIE_SECURE` env var is unset and a login response is sent
- **THEN** the `Set-Cookie` header includes `Secure`, `HttpOnly`, and `SameSite=Lax` attributes

#### Scenario: Cookie omits Secure when env var is "false"
- **WHEN** `SESSION_COOKIE_SECURE=false` and a login response is sent
- **THEN** the `Set-Cookie` header includes `HttpOnly` and `SameSite=Lax` but NOT `Secure`
