## Prerequisites

This change builds on `multi-user-auth-core`. Ensure that change is archived (or at minimum, all its tasks are complete) before starting.

## 1. @require_admin middleware

- [ ] 1.1 RED — `tests/test_middleware_require_admin.py`: 401 when unauthenticated; 403 when authenticated but `role='member'`; 200 + `g.user` set when authenticated admin. 401 response clears cookie; 403 preserves it.
- [ ] 1.2 GREEN — extend `backend/app/middleware.py` with `@require_admin` that wraps `@require_auth` then checks `g.user.role == 'admin'`.
- [ ] 1.3 Run pytest — green.
- [ ] 1.4 Run superpowers:requesting-code-review on the diff for group 1.

## 2. Admin user CRUD endpoints

- [ ] 2.1 RED — `tests/test_admin_users_list.py`: `GET /api/admin/users` returns sorted-by-invited_at-DESC array with computed `has_google` / `has_password` / `invited_by_email` fields; 401 without auth; 403 as member.
- [ ] 2.2 RED — `tests/test_admin_users_invite.py`: 201 + `{user, invite_url}` for new email; 409 + `{existing}` for duplicate (same canonicalized email); email canonicalization round-trip; admin self can't be invited (just returns 409 since they exist); the existing token is invalidated when resending via dup-409 caller flow (handled by resend-invite endpoint, not this one).
- [ ] 2.3 RED — `tests/test_admin_users_patch.py`: 200 on valid role/status change; 400 on (cannot change own role / cannot disable self / cannot demote only admin / invalid status enum); disabled user's next request returns 401 via core's `@require_auth`.
- [ ] 2.4 RED — `tests/test_admin_users_delete.py`: 400 if active (must disable first); 400 if self; 400 if only admin; 204 on success cascades private_entries/notes/chat_sessions/chat_messages + Qdrant filter-delete by user_id; knowledge files preserved; Qdrant before SQLite ordering tested by mocking SQLite to fail and asserting Qdrant was already cleaned.
- [ ] 2.5 RED — `tests/test_admin_users_resend_invite.py`: 200 + new invite_url for `status='invited'` user; old token marked used; new token created with fresh expiry. 400 when status != 'invited'.
- [ ] 2.6 GREEN — `backend/app/routes/admin_users.py` implementing 5 endpoints: GET, POST, PATCH /:id, DELETE /:id, POST /:id/resend-invite. All decorated with `@require_admin`. Register blueprint in app factory.
- [ ] 2.7 GREEN — extend `backend/app/services/user_service.py` with `delete_user_cascading(user_id)` that runs Qdrant filter-delete first, then SQLite cascade. Surface partial failures explicitly.
- [ ] 2.8 Run pytest — green; full suite no regressions.
- [ ] 2.9 Run superpowers:requesting-code-review on the diff for group 2 (this is the security-critical group; review carefully).

## 3. useAdminUsersStore

- [ ] 3.1 RED — `frontend/tests/stores/adminUsers.test.js`: each action calls the right endpoint with the right body; `inviteUser` returns `{conflict: existing}` (not throws) on 409; `deleteUser` removes the row from `store.users` after success; `updateUser` updates the row in place.
- [ ] 3.2 GREEN — `frontend/src/stores/adminUsers.js`. Inject axios instance for testability (matching pattern from `chat.js`, `auth.js`).
- [ ] 3.3 Run vitest — green.
- [ ] 3.4 Run superpowers:requesting-code-review on the diff for group 3.

## 4. InviteUserModal + DeleteUserModal components

- [ ] 4.1 RED — `frontend/tests/components/InviteUserModal.test.js`: form submission calls `adminUsers.inviteUser`; success state shows invite URL + copy button (data-copy-btn); 409 with status='active' shows disabled "已激活" button; 409 with status='invited' shows 【重发邀请】 calling `adminUsers.resendInvite`; 409 with status='disabled' shows 【重新启用】.
- [ ] 4.2 GREEN — `frontend/src/components/InviteUserModal.vue` per mock §2 ("+邀请用户" 弹窗的三个状态").
- [ ] 4.3 RED — `frontend/tests/components/DeleteUserModal.test.js`: type-to-confirm gates the red 【永久删除】 button; success closes modal; error renders inline.
- [ ] 4.4 GREEN — `frontend/src/components/DeleteUserModal.vue` per mock "删除确认" section.
- [ ] 4.5 Run vitest — green.
- [ ] 4.6 Run superpowers:requesting-code-review on the diff for group 4.

## 5. AdminUsersView

- [ ] 5.1 RED — `frontend/tests/views/AdminUsersView.test.js` desktop:
  - On mount, calls `adminUsers.fetchUsers`.
  - Renders 4-fixture-user table with correct color coding per status.
  - Self-row has "不能改自己" placeholder (no buttons).
  - Demote-only-admin: button has `disabled` attr when `users.filter(role='admin').length === 1`.
  - Click 【+ 邀请用户】 opens InviteUserModal; click 【删除】 opens DeleteUserModal.
  - Per-state action buttons fire correct store actions.
- [ ] 5.2 RED — `frontend/tests/views/AdminUsersView.test.js` mobile:
  - At viewport 393px, table is hidden, cards visible.
  - 【+】 button in header opens bottom sheet (not modal).
  - Cards stack with the same status color tints + appropriate per-state actions.
- [ ] 5.3 GREEN — `frontend/src/views/AdminUsersView.vue` per mock §2. Use `<InviteUserModal>` and `<DeleteUserModal>` components from group 4.
- [ ] 5.4 Run vitest — green.
- [ ] 5.5 Run superpowers:requesting-code-review on the diff for group 5.

## 6. AppLayout 5th sidebar item + router registration

- [ ] 6.1 RED — `frontend/tests/components/AppLayout.test.js` extension: at desktop viewport with admin user, sidebar has 5 nav links (the existing 4 + "用户管理"); with member user, only 4; logged-out, only 4. Mobile bottom-tab unchanged at 5 items.
- [ ] 6.2 GREEN — `frontend/src/components/AppLayout.vue`: insert conditional 5th `<router-link to="/admin/users" v-if="auth.currentUser?.role === 'admin'">` in sidebar nav.
- [ ] 6.3 RED — `frontend/tests/router-admin-route.test.js`: `/admin/users` registered with `meta.requiresAdmin: true`; admin navigation succeeds; member redirected to `/chat`; unauthenticated redirected to `/login?redirect=/admin/users`.
- [ ] 6.4 GREEN — `frontend/src/router/index.js`: register the route. Verify the `meta.requiresAdmin` guard already exists from core change and works correctly.
- [ ] 6.5 Run vitest — full suite green.
- [ ] 6.6 Run superpowers:requesting-code-review on the diff for group 6.

## 7. CLAUDE.md update — UI is primary, CLI is fallback

- [ ] 7.1 RED — `tests/test_claude_md.py` extension: assert CLAUDE.md contains a phrase like "primary path: /admin/users" AND "CLI is emergency fallback".
- [ ] 7.2 GREEN — update `CLAUDE.md` to reposition the CLI Pitfall: "use `/admin/users` web UI to invite/manage users; CLI (`python -m app.cli.invite_user`) is kept for emergencies (admin locked out, JS broken, debugging)".
- [ ] 7.3 Run pytest — green.
- [ ] 7.4 Run superpowers:requesting-code-review on the diff for group 7.

## 8. E2E for the admin → member flow

- [ ] 8.1 RED — `frontend/e2e/admin-flow.spec.ts`: log in as admin (using fixture from core's auth-fixture.ts); navigate to /admin/users; click 【+ 邀请用户】; submit form; assert invite_url visible; copy URL; in a new context (different storage) navigate to that URL; submit accept-invite; navigate back to /admin/users in admin context; assert the new user shows as `active`. Also test PATCH (disable then re-enable) and DELETE (with type-to-confirm).
- [ ] 8.2 GREEN — implement any small UI tweaks needed; primarily this is verification.
- [ ] 8.3 Run `npm run e2e -- admin-flow.spec.ts` — green.
- [ ] 8.4 Run superpowers:requesting-code-review on the e2e spec.

## 9. Verification & ship

- [ ] 9.1 Run full backend pytest — should be ~298 (218 + ~80 from this change) all green.
- [ ] 9.2 Run full frontend vitest — should be ~210 (169 + ~40 from this change) all green.
- [ ] 9.3 Run full Playwright — desktop + mobile + new admin-flow spec all green.
- [ ] 9.4 Manual smoke on dev stack (`npm run dev:up`):
  - Log in as admin (from core).
  - Navigate to /admin/users via 5th sidebar nav.
  - Invite a fake test user; copy URL.
  - In another browser profile / incognito, paste URL → /accept-invite → set password → land /chat.
  - Back in admin browser: refresh /admin/users; new user shown as active.
  - Disable the test user; their next API request → 401 (verify in dev tools).
  - Re-enable the test user.
  - Disable again, then delete (type-to-confirm); verify their data is gone (Qdrant inspector + sqlite query).
- [ ] 9.5 Run superpowers:verification-before-completion: tests green; no console.log; spec ↔ implementation consistent; CLAUDE.md updated.
- [ ] 9.6 Final superpowers:requesting-code-review on the entire change diff.

## Ship

- [ ] S.1 `./scripts/build-and-push.sh` — pushes new api + frontend images.
- [ ] S.2 NAS UGOS Docker app → Project python-agent → Pull → Apply.
- [ ] S.3 Live test on `http://10.0.0.20:8910` — log in (existing admin from core), verify 5th sidebar nav appears, invite a real family member, verify their flow.
- [ ] S.4 git add / commit with `feat: multi-user-auth-admin-ui` style message.
- [ ] S.5 git push.
- [ ] S.6 Update `docs/log/<date>.md` with the deployment summary.
- [ ] S.7 `openspec archive multi-user-auth-admin-ui`.
