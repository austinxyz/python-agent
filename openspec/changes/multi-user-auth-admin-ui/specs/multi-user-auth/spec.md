## ADDED Requirements

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
