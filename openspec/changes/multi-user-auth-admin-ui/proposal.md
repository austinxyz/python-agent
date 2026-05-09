## Why

`multi-user-auth-core` ships login + invite-via-CLI + per-user data isolation. Inviting members requires `docker exec ... python -m app.cli.invite_user` — workable for one-off invites but rough for ongoing user management (re-invite, change role, disable, delete). This change replaces the CLI flow with a real admin UI at `/admin/users`, adding the corresponding `/api/admin/users` REST endpoints.

This is the **second half** of the multi-user split. After this ships, the CLI tool stays in the codebase as an emergency fallback (e.g., admin locked out scenarios) but is no longer the primary path; CLAUDE.md updated accordingly.

Source of truth: [requirements doc](../../../docs/superpowers/specs/2026-05-09-multi-user-auth-requirements.md) §7. UI mocks: [mocks doc](../../../docs/superpowers/specs/mocks/2026-05-09-multi-user-auth-mocks.html) §2 — covers desktop list view, invite modal (3 states: form / success-with-URL / 409 duplicate), delete confirmation modal, mobile card list + bottom sheet invite. Hardening items deferred per the slim discussion (admin reset-password endpoint, audit log of admin actions, concurrent-invite race tests) remain out of scope.

## What Changes

### Backend routes (NEW under `/api/admin/`)
- `GET /api/admin/users` — return all users with `{id, email, name, picture_url, role, status, has_google, has_password, invited_at, invited_by_email, activated_at, last_login_at}`. Sorted by `invited_at DESC` (newest first).
- `POST /api/admin/users` — body `{email, role}`. Canonicalizes email. Returns 201 + `{user, invite_url}` on creation OR **409** + `{error: "user already exists", existing: {id, email, status, role}}` if email collides (admin UI uses this to offer context-aware actions).
- `PATCH /api/admin/users/:id` — body `{role?, status?}`. Cannot change own role (admin can't demote self). Cannot disable self. Cannot demote the only admin. Disabling sets `status='disabled'` (next request from that user's session returns 401 via `@require_auth` per-request status check from core change).
- `DELETE /api/admin/users/:id` — permanent. Requires `status='disabled'` first (refuses to delete `'active'`). Refuses to delete self. Cascades: deletes user's `private_entries`, `notes`, `chat_sessions`, `chat_messages`; runs Qdrant filter-delete on `private` collection by `user_id`. Knowledge files ingested by this user are NOT deleted (shared content; `user_id` becomes orphan, audit-friendly).
- `POST /api/admin/users/:id/resend-invite` — only valid when `status='invited'`. Marks any existing `invite_tokens` row used; creates a new token with fresh 7-day expiry. Returns `{invite_url}`.

All endpoints decorated with `@require_admin` (extends `@require_auth` from core change with `g.user.role == 'admin'` check). 401 → 403 fallthrough behavior.

### Frontend
- **NEW `AdminUsersView.vue`** at `/admin/users`. Layout follows the project's two-column convention with the existing AppLayout sidebar visible. Main pane: navy hero band + count summary + 【+ 邀请用户】CTA + table (mobile: cards). Per-row actions per user state per the mocks. Color coding: `active` green dot, `invited` orange dot + yellow row tint, `disabled` gray dot + 70% opacity.
- **NEW invite modal** with three render states: form / success-with-invite-URL (with copy button) / 409 duplicate-email (with context-aware sub-action: "重新发送邀请" if existing is invited, "已激活、无需重邀" disabled button if active, "重新启用" button if disabled).
- **NEW delete confirmation modal** with two-step confirm: shows what gets / doesn't get deleted, requires user to type the username (first 2 chars before `@`) to enable the red 【永久删除】button.
- **NEW `useAdminUsersStore`** Pinia store: state `{users, loading, error}`, actions `fetchUsers`, `inviteUser`, `updateUser`, `deleteUser`, `resendInvite`. Reuses the auth store's pattern (axios injected for testability).
- **MODIFIED `AppLayout.vue`**: 5th nav item `用户管理` (gear/settings icon) appears in the desktop sidebar nav for `auth.currentUser?.role === 'admin'`. Mobile: the same admin link appears INSIDE the `/me` view (which already has the slot for it from the core change), NOT as an additional bottom tab.
- **MODIFIED `router/index.js`**: register `/admin/users`. The router's pre-existing `/admin/*` admin-only guard (added in core change but unused there) now actually has a route to protect.

### Mobile-specific
- Invite is a bottom sheet (slides up from bottom) rather than a modal — matches the rest of the mobile app's interaction patterns (PrivateView already uses bottom-sheet style).
- Delete confirmation on mobile is a bottom sheet too (full-width, easier to tap accurately).

### CLI tool — kept as fallback
- `python -m app.cli.invite_user` continues to work after this change ships (no removal). CLAUDE.md updates: "primary path is /admin/users; CLI is the emergency fallback when admin can't access UI (e.g., locked out, JS broken, debugging)".

## Capabilities

### New Capabilities
None.

### Modified Capabilities
- `multi-user-auth`: gains the 5 admin endpoints with their authorization rules (admin role, can't-modify-self constraints).
- `frontend-scaffold`: gains AdminUsersView, useAdminUsersStore, the conditional 5th sidebar nav item for admins, and the `/admin/users` route registration.

## Impact

- **Files added (backend):** `backend/app/routes/admin_users.py`, plus `@require_admin` helper in the existing `middleware.py`.
- **Files added (frontend):** `frontend/src/views/AdminUsersView.vue`, `frontend/src/stores/adminUsers.js`, `frontend/src/components/InviteUserModal.vue`, `frontend/src/components/DeleteUserModal.vue`.
- **Files modified (backend):** `user_service.py` gains `delete_user_cascading(user_id)` that handles SQLite + Qdrant deletes atomically; `app/__init__.py` registers the new blueprint.
- **Files modified (frontend):** `AppLayout.vue` (5th nav item conditional on admin), `router/index.js` (register route + verify the /admin/* guard works), `views/MeView.vue` (admin link to /admin/users only when role=admin — was already in core's MeView template; this change verifies it works post-route-registration).
- **CLI tool kept:** no removal. CLAUDE.md updates to position UI as primary path.
- **Tests added:** ~80 backend pytest cases (5 endpoints × ~16 cases for happy/edge/auth/admin-self-protection) + ~40 frontend vitest cases (AdminUsersView + adminUsersStore + 2 modal components) + 1 Playwright E2E spec covering invite-as-admin → accept-as-member → admin sees the new active user.
- **Operational:** ship + Pull → Apply on NAS as usual. No data migration. After ship, admin can invite via UI; existing CLI flow keeps working as a safety net.
- **Out of scope** (deferred):
  - Admin reset-password endpoint (admin disables + re-invites for password recovery — same as core)
  - Admin operation audit log (`auth-audit-log` change)
  - Concurrent-invite race test (the UNIQUE constraint catches it; spec describes the 409 response but a dedicated race test isn't shipped)
  - Bulk invite / CSV import (out of personal scale)
  - Admin can set initial password directly (dropped in slim — invite URL only)

Backlog references unchanged from `multi-user-auth-core`'s list.
