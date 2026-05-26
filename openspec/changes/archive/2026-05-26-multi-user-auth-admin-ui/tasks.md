## Prerequisites

This change builds on `multi-user-auth-core`. Ensure that change is archived (or at minimum, all its tasks are complete) before starting.

## 1. @require_admin middleware

### Contract
- **Spec**:
  - `@require_admin` SHALL return 401 (clearing session cookie) when the request is unauthenticated
  - `@require_admin` SHALL return 403 (preserving session cookie) when authenticated but `role != 'admin'`
  - `@require_admin` SHALL set `g.user` and proceed when `role == 'admin'` and `status == 'active'`
- **Runtime**: `cd backend && pytest tests/test_middleware_require_admin.py -v` → all 4 scenarios pass
- **Code**: Two-stage decorator — `_validate_session()` first (401 path), then role check (403 path). Design decision §2: the 401 vs 403 split matters because the axios 401 interceptor redirects to /login; 403 must NOT redirect.
- **Threshold**: 80

- [x] 1.0 CONTRACT — write `openspec/changes/multi-user-auth-admin-ui/contracts/group-1.md` with the ### Contract block above; confirm all three fields (Spec, Runtime, Code) are non-empty before proceeding
- [x] 1.1 RED — `tests/test_middleware_require_admin.py`: 401 when unauthenticated; 403 when authenticated but `role='member'`; 200 + `g.user` set when authenticated admin. 401 response clears cookie; 403 preserves it.
- [x] 1.2 GREEN — extend `backend/app/middleware.py` with `@require_admin` that wraps `@require_auth` then checks `g.user.role == 'admin'`.
- [x] 1.3 Run pytest — green.
- [x] 1.E EVAL — spawn evaluator subagent (haiku); reads `contracts/group-1.md` + `specs/multi-user-auth/spec.md` + `design.md` + group-1 diff; invokes `superpowers:requesting-code-review` (CRITICAL/HIGH = BLOCK); scores Spec/Runtime/Code; total ≥ 80 → PASS; < 80 → append FIX tasks + retry (max 3 attempts, plateau < 5pt = escalate)

## 2. Admin user CRUD endpoints

### Contract
- **Spec**:
  - GET /api/admin/users SHALL return all users sorted `invited_at DESC` with computed `has_google` / `has_password` / `invited_by_email` fields; 401 without auth; 403 as member
  - POST /api/admin/users SHALL return 201 + `{user, invite_url}` for new email; 409 + `{error, existing: {id, email, status, role}}` for duplicate (after email canonicalization)
  - PATCH /api/admin/users/:id SHALL reject self-role-change / self-disable / only-admin-demote / invalid status enum with 400; return 200 + updated user on valid change
  - DELETE /api/admin/users/:id SHALL reject active user (400 "must be disabled first"), self (400), only-admin (400); cascade-delete `private_entries` / `notes` / `chat_sessions` / `chat_messages` + Qdrant filter-delete; preserve knowledge files; Qdrant delete BEFORE SQLite
  - POST /api/admin/users/:id/resend-invite SHALL return 400 for `status != 'invited'`; 200 + new `invite_url` with old token invalidated for `status='invited'`
- **Runtime**: `cd backend && pytest tests/test_admin_users_list.py tests/test_admin_users_invite.py tests/test_admin_users_patch.py tests/test_admin_users_delete.py tests/test_admin_users_resend_invite.py -v` → all scenarios pass, full suite no regressions
- **Code**: Design §3 (delete requires disabled-first), §5 (knowledge files preserved), §6 (409 context-aware), R-04 (Qdrant before SQLite ordering for partial-failure recovery). Security-critical group: all endpoints decorated with `@require_admin`; PATCH self-protection rules are the primary defense against privilege escalation.
- **Threshold**: 80

- [x] 2.0 CONTRACT — write `openspec/changes/multi-user-auth-admin-ui/contracts/group-2.md` with the ### Contract block above; confirm all three fields non-empty
- [x] 2.1 RED — `tests/test_admin_users_list.py`: `GET /api/admin/users` returns sorted-by-invited_at-DESC array with computed `has_google` / `has_password` / `invited_by_email` fields; 401 without auth; 403 as member.
- [x] 2.2 RED — `tests/test_admin_users_invite.py`: 201 + `{user, invite_url}` for new email; 409 + `{existing}` for duplicate (same canonicalized email); email canonicalization round-trip; admin self can't be invited (just returns 409 since they exist); the existing token is invalidated when resending via dup-409 caller flow (handled by resend-invite endpoint, not this one).
- [x] 2.3 RED — `tests/test_admin_users_patch.py`: 200 on valid role/status change; 400 on (cannot change own role / cannot disable self / cannot demote only admin / invalid status enum); disabled user's next request returns 401 via core's `@require_auth`.
- [x] 2.4 RED — `tests/test_admin_users_delete.py`: 400 if active (must disable first); 400 if self; 400 if only admin; 204 on success cascades private_entries/notes/chat_sessions/chat_messages + Qdrant filter-delete by user_id; knowledge files preserved; Qdrant before SQLite ordering tested by mocking SQLite to fail and asserting Qdrant was already cleaned.
- [x] 2.5 RED — `tests/test_admin_users_resend_invite.py`: 200 + new invite_url for `status='invited'` user; old token marked used; new token created with fresh expiry. 400 when status != 'invited'.
- [x] 2.6 GREEN — `backend/app/routes/admin_users.py` implementing 5 endpoints: GET, POST, PATCH /:id, DELETE /:id, POST /:id/resend-invite. All decorated with `@require_admin`. Register blueprint in app factory.
- [x] 2.7 GREEN — extend `backend/app/services/user_service.py` with `delete_user_cascading(user_id)` that runs Qdrant filter-delete first, then SQLite cascade. Surface partial failures explicitly.
- [x] 2.8 Run pytest — green; full suite no regressions.
- [x] 2.E EVAL — spawn evaluator subagent (haiku); reads `contracts/group-2.md` + `specs/multi-user-auth/spec.md` + `design.md` + group-2 diff; invokes `superpowers:requesting-code-review` (CRITICAL/HIGH = BLOCK); scores Spec/Runtime/Code; total ≥ 80 → PASS; < 80 → append FIX tasks + retry (max 3 attempts, plateau < 5pt = escalate)

## 3. useAdminUsersStore

### Contract
- **Spec**:
  - `inviteUser(email, role)` SHALL return `{conflict: existing}` (not throw) on 409; `store.error` remains null
  - `deleteUser(id)` SHALL remove the matching user from `store.users` after success
  - `updateUser(id, patch)` SHALL update the matching row in `store.users` in place
  - All actions SHALL call the correct API endpoints with the correct HTTP methods and request bodies
  - `fetchUsers()` SHALL populate `store.users` from GET /api/admin/users
- **Runtime**: `cd frontend && npm test -- tests/stores/adminUsers.test.js` → all assertions pass
- **Code**: 409 catch-and-return (not rethrow) is critical for the InviteUserModal 3-state flow. Axios instance injected as a dependency for testability — same pattern as `auth.js` / `chat.js`.
- **Threshold**: 80

- [x] 3.0 CONTRACT — write `openspec/changes/multi-user-auth-admin-ui/contracts/group-3.md` with the ### Contract block above; confirm all three fields non-empty
- [x] 3.1 RED — `frontend/tests/stores/adminUsers.test.js`: each action calls the right endpoint with the right body; `inviteUser` returns `{conflict: existing}` (not throws) on 409; `deleteUser` removes the row from `store.users` after success; `updateUser` updates the row in place.
- [x] 3.2 GREEN — `frontend/src/stores/adminUsers.js`. Inject axios instance for testability (matching pattern from `chat.js`, `auth.js`).
- [x] 3.3 Run vitest — green.
- [x] 3.F1 FIX — FALSE POSITIVE: axios instance has `baseURL: '/api'` (see `src/api/index.js:3`), so `/admin/users` correctly resolves to `/api/admin/users`. No code change needed.
- [x] 3.E EVAL — spawn evaluator subagent (haiku); reads `contracts/group-3.md` + `specs/frontend-scaffold/spec.md` + `design.md` + group-3 diff; invokes `superpowers:requesting-code-review` (CRITICAL/HIGH = BLOCK); scores Spec/Runtime/Code; total ≥ 80 → PASS; < 80 → append FIX tasks + retry (max 3 attempts, plateau < 5pt = escalate)

## 4. InviteUserModal + DeleteUserModal components

### Contract
- **Spec**:
  - InviteUserModal heading text SHALL be `邀请新用户`; success heading SHALL be `✓ 邀请已生成`; copy button classes match `/bg-notion-primary/`; hint text contains `7 天后过期`
  - On 409 `status='active'`: disabled button text SHALL be `已激活，无需邀请`
  - On 409 `status='invited'`: 【重发邀请】button SHALL call `adminUsers.resendInvite(id)`
  - On 409 `status='disabled'`: 【重新启用】button SHALL call `adminUsers.updateUser(id, {status:'active'})`
  - DeleteUserModal heading classes SHALL match `/text-notion-error/` with text `⚠ 永久删除用户`; warning box classes match `/bg-notion-tint-rose/`; destructive CTA classes match `/bg-notion-error/`
  - Delete CTA SHALL be disabled until input value === local part of the email (substring before `@`)
- **Runtime**: `cd frontend && npm test -- tests/components/InviteUserModal.test.js tests/components/DeleteUserModal.test.js` → all assertions pass
- **Code**: Design §6 (409 context-aware sub-actions), §4 (type-to-confirm localpart), design.md §UI Fidelity locked tokens. VISUAL DIFF tasks verify rendered output against `2026-05-09-multi-user-auth-mocks.html#admin-users`.
- **Threshold**: 70

- [x] 4.0 CONTRACT — write `openspec/changes/multi-user-auth-admin-ui/contracts/group-4.md` with the ### Contract block above; confirm all three fields non-empty
- [x] 4.1 RED — `frontend/tests/components/InviteUserModal.test.js`: form submission calls `adminUsers.inviteUser`; success state shows visible text matching `/✓ 邀请已生成/`, code block with URL, copy button (data-copy-btn) classes match `/bg-notion-primary/`, hint text contains `7 天后过期`; 409 with status='active' shows disabled button with text `已激活，无需邀请`; 409 with status='invited' shows 【重发邀请】 calling `adminUsers.resendInvite`; 409 with status='disabled' shows 【重新启用】 calling `adminUsers.updateUser` with `{status: 'active'}`. Modal heading classes match `/text-notion-ink/` with text `邀请新用户`.
- [x] 4.2 MOCK — open `docs/superpowers/specs/mocks/2026-05-09-multi-user-auth-mocks.html#admin-users` and locate the "+ 邀请用户 弹窗的三个状态" 3-panel section. Note: form (radio active = `bg-notion-tint-lavender border-notion-primary`), success (URL in `<code>` with copy button right of it), 409 (disabled button styling).
- [x] 4.3 GREEN — `frontend/src/components/InviteUserModal.vue`.
- [x] 4.4 VISUAL DIFF — In `/admin/users` (admin-only flow tested in group 9), open invite modal; deliberately submit a duplicate to trigger 409; eyeball each of 3 states against mock; fix drift.
- [x] 4.5 RED — `frontend/tests/components/DeleteUserModal.test.js`: type-to-confirm gates the red 【永久删除】 button (disabled until input value === local-part); heading classes match `/text-notion-error/` with text `⚠ 永久删除用户`; warning box classes match `/bg-notion-tint-rose/`; destructive button classes match `/bg-notion-error/`; success closes modal; error renders inline.
- [x] 4.6 MOCK — same anchor, locate "删除确认" section. Note: red destructive CTA; type-to-confirm input; pink warning box with bullet lists.
- [x] 4.7 GREEN — `frontend/src/components/DeleteUserModal.vue`.
- [x] 4.8 VISUAL DIFF — Trigger delete confirmation on a disabled user; verify inputs lock the button; eyeball modal vs mock.
- [x] 4.9 Run vitest — green.
- [x] 4.E EVAL — spawn evaluator subagent (haiku); reads `contracts/group-4.md` + `specs/frontend-scaffold/spec.md` + `design.md` + group-4 diff; invokes `superpowers:requesting-code-review` (CRITICAL/HIGH = BLOCK); scores Spec/Runtime/Code; total ≥ 70 → PASS; < 70 → append FIX tasks + retry (max 3 attempts, plateau < 5pt = escalate)

## 5. AdminUsersView

### Contract
- **Spec**:
  - On mount SHALL call `adminUsers.fetchUsers()`
  - Hero band classes SHALL match `/bg-notion-brand-navy/` + `/text-notion-on-dark/`; heading text `用户管理`; CTA text `+ 邀请用户` with classes matching `/bg-notion-primary/`
  - Self-row SHALL show `不能改自己` text, no action buttons
  - `invited` row SHALL have `/bg-notion-tint-yellow/` background; `disabled` row SHALL have `/bg-notion-surface-soft/` + `/opacity-70/`
  - Admin role badge classes SHALL match `/bg-notion-tint-lavender/` + `/text-notion-brand-purple-800/`; member badge `/bg-notion-tint-gray/` + `/text-notion-slate/`
  - At 393px viewport: table element SHALL be hidden, card list SHALL be visible
  - Demote-only-admin 【↓ member】 button SHALL have `disabled` attribute when only 1 admin in the users list
- **Runtime**: `cd frontend && npm test -- tests/views/AdminUsersView.test.js` → all scenarios pass
- **Code**: design.md §UI Fidelity full token list; 6-column desktop table; self-row detection compares `user.id === auth.currentUser.id`; R-01 (only-admin guard mirrored in UI via computed); VISUAL DIFF verifies rendered output against mocks.
- **Threshold**: 70

- [x] 5.0 CONTRACT — write `openspec/changes/multi-user-auth-admin-ui/contracts/group-5.md` with the ### Contract block above; confirm all three fields non-empty
- [x] 5.1 RED — `frontend/tests/views/AdminUsersView.test.js` desktop:
  - On mount, calls `adminUsers.fetchUsers`.
  - Renders 4-fixture-user table with correct color coding per status.
  - Self-row has "不能改自己" placeholder (no buttons).
  - Demote-only-admin: button has `disabled` attr when `users.filter(role='admin').length === 1`.
  - Click 【+ 邀请用户】 opens InviteUserModal; click 【删除】 opens DeleteUserModal.
  - Per-state action buttons fire correct store actions.
- [x] 5.2 RED — `frontend/tests/views/AdminUsersView.test.js` mobile:
  - At viewport 393px, table is hidden, cards visible.
  - 【+】 button in header opens bottom sheet (not modal).
  - Cards stack with the same status color tints + appropriate per-state actions.
- [x] 5.3 MOCK — open `mocks doc#admin-users`. Note: navy hero band with right-aligned 【+ 邀请用户】 CTA; table column widths `280px 1fr 90px 110px 130px 140px`; row tints by status (active=plain, invited=`bg-notion-tint-yellow`, disabled=`bg-notion-surface-soft opacity-70` + line-through email); badge tokens (admin=lavender, member=gray); per-state action buttons. Mobile cards use the same color coding. Self-row shows `不能改自己` placeholder text in the actions cell.
- [x] 5.4 GREEN — `frontend/src/views/AdminUsersView.vue`. Use `<InviteUserModal>` and `<DeleteUserModal>` components from group 4.
- [x] 5.5 VISUAL DIFF — `/admin/users` with 3-4 fixture users covering each status; eyeball desktop table against mock; switch to mobile viewport (Chrome DevTools 393×852); eyeball cards. Verify self-row shows "不能改自己" not buttons. Fix drift.
- [x] 5.6 Run vitest — green.
- [x] 5.E EVAL — spawn evaluator subagent (haiku); reads `contracts/group-5.md` + `specs/frontend-scaffold/spec.md` + `design.md` + group-5 diff; invokes `superpowers:requesting-code-review` (CRITICAL/HIGH = BLOCK); scores Spec/Runtime/Code; total ≥ 70 → PASS; < 70 → append FIX tasks + retry (max 3 attempts, plateau < 5pt = escalate)

## 6. AppLayout 5th sidebar item + router registration

### Contract
- **Spec**:
  - AppLayout SHALL render 5th sidebar nav item `用户管理` only when `auth.currentUser?.role === 'admin'`; member and logged-out users see exactly 4 items
  - Active state on `/admin/*` routes SHALL use classes matching `/bg-notion-tint-lavender/` + `/text-notion-brand-purple-800/`
  - `/admin/users` route SHALL be registered with `meta.requiresAdmin: true`; member navigating there SHALL be redirected to `/chat`; unauthenticated to `/login?redirect=/admin/users`
- **Runtime**: `cd frontend && npm test -- tests/components/AppLayout.test.js tests/router-admin-route.test.js` → all assertions pass
- **Code**: `v-if="auth.currentUser?.role === 'admin'"` conditional on 5th nav `<router-link>`; existing `/admin/*` guard in `router/index.js` `beforeEach` already handles the redirect — just need to register the route. VISUAL DIFF verifies 5 vs 4 nav items in browser.
- **Threshold**: 70

- [x] 6.0 CONTRACT — write `openspec/changes/multi-user-auth-admin-ui/contracts/group-6.md` with the ### Contract block above; confirm all three fields non-empty
- [x] 6.1 RED — `frontend/tests/components/AppLayout.test.js` extension: at desktop viewport with admin user, sidebar has 5 nav links (the existing 4 + "用户管理"); with member user, only 4; logged-out, only 4. Mobile bottom-tab unchanged at 5 items.
- [x] 6.2 MOCK — open `mocks doc#admin-users`, look at the desktop sidebar in the table screenshot. Note: 5th nav item "⚙ 用户管理" appears below 私有数据; active state matches existing pattern `bg-notion-tint-lavender text-notion-brand-purple-800`.
- [x] 6.3 GREEN — `frontend/src/components/AppLayout.vue`: insert conditional 5th `<router-link to="/admin/users" v-if="auth.currentUser?.role === 'admin'">` in sidebar nav.
- [x] 6.4 VISUAL DIFF — at desktop, log in as admin (5 nav items visible) and as member (4 only). Tap into /admin/users; verify active state styling.
- [x] 6.5 RED — `frontend/tests/router-admin-route.test.js`: `/admin/users` registered with `meta.requiresAdmin: true`; admin navigation succeeds; member redirected to `/chat`; unauthenticated redirected to `/login?redirect=/admin/users`.
- [x] 6.6 GREEN — `frontend/src/router/index.js`: register the route. Verify the `meta.requiresAdmin` guard already exists from core change and works correctly.
- [x] 6.7 Run vitest — full suite green.
- [x] 6.E EVAL — spawn evaluator subagent (haiku); reads `contracts/group-6.md` + `specs/frontend-scaffold/spec.md` + `design.md` + group-6 diff; invokes `superpowers:requesting-code-review` (CRITICAL/HIGH = BLOCK); scores Spec/Runtime/Code; total ≥ 70 → PASS; < 70 → append FIX tasks + retry (max 3 attempts, plateau < 5pt = escalate)

## 7. CLAUDE.md update — UI is primary, CLI is fallback

### Contract
- **Spec**:
  - CLAUDE.md SHALL contain language positioning `/admin/users` web UI as the primary path for user management
  - CLAUDE.md SHALL contain language positioning the CLI (`python -m app.cli.invite_user`) as emergency fallback (admin locked out / JS broken / debugging)
- **Runtime**: `cd backend && pytest tests/test_claude_md.py -v` → content assertions pass
- **Code**: Documentation-only update; no production code risk. Critical for future sessions: without this, agents default back to CLI which breaks the multi-user UX intent established by this change.
- **Threshold**: 80

- [x] 7.0 CONTRACT — write `openspec/changes/multi-user-auth-admin-ui/contracts/group-7.md` with the ### Contract block above; confirm all three fields non-empty
- [x] 7.1 RED — `tests/test_claude_md.py` extension: assert CLAUDE.md contains a phrase like "primary path: /admin/users" AND "CLI is emergency fallback".
- [x] 7.2 GREEN — update `CLAUDE.md` to reposition the CLI Pitfall: "use `/admin/users` web UI to invite/manage users; CLI (`python -m app.cli.invite_user`) is kept for emergencies (admin locked out, JS broken, debugging)".
- [x] 7.3 Run pytest — green.
- [x] 7.E EVAL — spawn evaluator subagent (haiku); reads `contracts/group-7.md` + `specs/multi-user-auth/spec.md` + `design.md` + group-7 diff; invokes `superpowers:requesting-code-review` (CRITICAL/HIGH = BLOCK); scores Spec/Runtime/Code; total ≥ 80 → PASS; < 80 → append FIX tasks + retry (max 3 attempts, plateau < 5pt = escalate)

## 8. E2E for the admin → member flow

### Contract
- **Spec**:
  - E2E SHALL cover: admin login → /admin/users → invite new user → accept invite as new user (separate browser context) → admin sees new user as `active`
  - E2E SHALL cover: admin PATCH (disable a user, then re-enable)
  - E2E SHALL cover: admin DELETE with type-to-confirm (disable user first, then delete with matching localpart input)
- **Runtime**: `cd frontend && npm run e2e -- admin-flow.spec.ts` → all scenarios green
- **Code**: Uses auth fixtures from core (`auth-fixture.ts`). New browser context for accept-invite flow (separate storage). `__e2e_*` prefix for test users; `afterEach` cleanup even on failure.
- **Threshold**: 70

- [x] 8.0 CONTRACT — write `openspec/changes/multi-user-auth-admin-ui/contracts/group-8.md` with the ### Contract block above; confirm all three fields non-empty
- [x] 8.1 RED — `frontend/e2e/admin-flow.spec.ts`: log in as admin (using fixture from core's auth-fixture.ts); navigate to /admin/users; click 【+ 邀请用户】; submit form; assert invite_url visible; copy URL; in a new context (different storage) navigate to that URL; submit accept-invite; navigate back to /admin/users in admin context; assert the new user shows as `active`. Also test PATCH (disable then re-enable) and DELETE (with type-to-confirm).
- [x] 8.2 GREEN — implement any small UI tweaks needed; primarily this is verification.
- [x] 8.3 Run `npm run e2e -- admin-flow.spec.ts` — green. 3/3 passed.
- [x] 8.E EVAL — spawn evaluator subagent (haiku); reads `contracts/group-8.md` + `specs/multi-user-auth/spec.md` + `specs/frontend-scaffold/spec.md` + `design.md` + group-8 diff; invokes `superpowers:requesting-code-review` (CRITICAL/HIGH = BLOCK); scores Spec/Runtime/Code; total ≥ 70 → PASS; < 70 → append FIX tasks + retry (max 3 attempts, plateau < 5pt = escalate)

## 9. Verification & ship

- [x] 9.1 Run full backend pytest — 354 passed, 1 skipped (all green; test_export_volumes_script.py skipped due to Windows OS limitation).
- [x] 9.2 Run full frontend vitest — 273 passed (26 files, all green).
- [x] 9.3 Run full Playwright — 59 passed (chromium desktop + mobile-chrome, all green including new admin-flow spec).
- [x] 9.4 Manual smoke on dev stack (`npm run dev:up`):
  - Log in as admin (from core).
  - Navigate to /admin/users via 5th sidebar nav.
  - Invite a fake test user; copy URL.
  - In another browser profile / incognito, paste URL → /accept-invite → set password → land /chat.
  - Back in admin browser: refresh /admin/users; new user shown as active.
  - Disable the test user; their next API request → 401 (verify in dev tools).
  - Re-enable the test user.
  - Disable again, then delete (type-to-confirm); verify their data is gone (Qdrant inspector + sqlite query).
- [x] 9.5 Run superpowers:verification-before-completion: tests green; no console.log; spec ↔ implementation consistent; CLAUDE.md updated.
- [x] 9.6 Final superpowers:requesting-code-review on the entire change diff. Fixed 2 HIGH issues (APP_BASE_URL for invite URLs; only-admin PATCH guard now filters disabled admins) + 3 MEDIUM (updateUser error handling, handleReEnable closes modal, E2E disable assertion).

## Ship

- [x] S.1 `./scripts/build-and-push.sh` — pushes new api + frontend images. Tag: v20260525-a0dddeb.
- [x] S.2 NAS UGOS Docker app → Project python-agent → Pull → Apply.
- [x] S.3 Live test on `http://10.0.0.20:8910` — invite + accept flow verified live.
- [x] S.4 git add / commit with `feat: multi-user-auth-admin-ui` style message. Commit: f78d9cd.
- [x] S.5 git push.
- [x] S.6 Update `docs/log/2026-05-26.md` with deployment summary.
- [ ] S.7 `openspec archive multi-user-auth-admin-ui`.
