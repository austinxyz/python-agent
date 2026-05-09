## ADDED Requirements

### Requirement: useAdminUsersStore Pinia store
The system SHALL provide `frontend/src/stores/adminUsers.js` exporting a Pinia store with state `{ users, loading, error }` and actions:
- `fetchUsers()` → GET /api/admin/users → populates users.
- `inviteUser(email, role)` → POST /api/admin/users → returns `{user, invite_url}` on 201; on 409, returns `{conflict: existing}` so the UI can branch on existing state without re-throwing.
- `updateUser(id, patch)` → PATCH /api/admin/users/:id → updates the user in store.
- `deleteUser(id)` → DELETE /api/admin/users/:id → removes from store.
- `resendInvite(id)` → POST /api/admin/users/:id/resend-invite → returns `{invite_url}`.

`users` is the array of user objects (full shape from GET /api/admin/users).

#### Scenario: 409 from invite is caught and returned as conflict, not error
- **WHEN** `adminUsers.inviteUser('linda@gmail.com', 'member')` and the API returns 409
- **THEN** the action's resolved value is `{conflict: {id, email, status, role}}` (not a thrown error); `store.error` remains null

#### Scenario: deleteUser removes the row from store after success
- **WHEN** `adminUsers.deleteUser('uuid-x')` resolves successfully
- **THEN** `store.users` no longer contains the user with id='uuid-x'

### Requirement: AdminUsersView at /admin/users
`frontend/src/views/AdminUsersView.vue` SHALL render the user management UI per the mocks (`docs/superpowers/specs/mocks/2026-05-09-multi-user-auth-mocks.html#admin-users`). Behavior:
- On mount, calls `adminUsers.fetchUsers()`.
- Renders a navy hero band (`bg-notion-brand-navy text-notion-on-dark`) with heading text `用户管理` + count summary template `<N> 个用户 · <X> admin · <Y> active · <Z> invited · <W> disabled` + 【+ 邀请用户】 CTA (`bg-notion-primary text-notion-on-primary`).
- Below: a table at `md+` (columns: 用户 / 姓名 / 角色 / 状态 / 最后登录 / 操作) or stacked cards at `md-`. Color coding: `active` row uses `text-notion-brand-green` status dot; `invited` row uses `bg-notion-tint-yellow` background tint + `text-notion-warning` accent; `disabled` row uses `bg-notion-surface-soft` + `opacity-70` + line-through email. Role badge: admin `bg-notion-tint-lavender text-notion-brand-purple-800`; member `bg-notion-tint-gray text-notion-slate`. Self-row right cell shows verbatim text `不能改自己`.
- Per-row actions follow state:
  - Self row (any status): right-side text "不能改自己" placeholder, no action buttons.
  - `active` member: 【↑ admin】(promote) and 【停用】 buttons.
  - `active` admin (not self): 【↓ member】 (demote) and 【停用】 buttons. Demote disabled when this is the only admin.
  - `invited`: 【重发】 (resend-invite) and 【取消】 (delete the invited row). Yellow row tint.
  - `disabled`: 【启用】 (re-activate) and 【删除】 (permanent delete with confirm). Gray row tint.
- 【+ 邀请用户】opens `InviteUserModal` (desktop) or bottom sheet (mobile).
- 【删除】opens `DeleteUserModal` (desktop) or bottom sheet (mobile) with type-to-confirm.

The view is gated by the router's admin guard — non-admin trying to navigate to /admin/users is redirected to /chat.

#### Scenario: Non-admin redirected away from /admin/users
- **WHEN** a member-role user navigates to /admin/users
- **THEN** the router redirects them to /chat (not even rendered)

#### Scenario: Self-row shows "不能改自己" placeholder
- **WHEN** AdminUsersView renders with `auth.currentUser` matching one of the user rows
- **THEN** that row's actions cell shows "不能改自己" text, no buttons

#### Scenario: Demote-only-admin button disabled in UI
- **WHEN** AdminUsersView renders with exactly 1 admin user and that admin is rendered as a row
- **THEN** the 【↓ member】 button on that row (if present) has `disabled` attribute set OR is hidden

#### Scenario: Mobile renders cards, not table
- **WHEN** AdminUsersView renders at viewport 393px
- **THEN** the table is hidden (`hidden md:block` or equivalent) and cards are visible (`block md:hidden`)

#### Scenario: Locked tokens + heading text
- **WHEN** AdminUsersView mounts
- **THEN** the hero band classes match `/bg-notion-brand-navy/`; visible text contains `用户管理` AND `+ 邀请用户`; the admin role badge classes match `/bg-notion-tint-lavender/` AND `/text-notion-brand-purple-800/`

### Requirement: InviteUserModal component
`frontend/src/components/InviteUserModal.vue` SHALL render an email input, a role radio (member / admin, default member), 【生成邀请链接】 CTA, 【取消】. Submit calls `adminUsers.inviteUser(email, role)`. Render branches by the returned value:
- Returned `{user, invite_url}` → render success state with heading `✓ 邀请已生成`, the URL in a code block + 【复制】 button (`bg-notion-primary`), and verbatim hint text `7 天后过期。如果对方没及时点，回列表"重发邀请"。`.
- Returned `{conflict: existing}` → render warning state with heading `⚠ 该用户已存在` and `existing.status`-aware sub-action button: `'invited'` → 【重发邀请】(calls resendInvite, `bg-notion-primary`); `'active'` → disabled button with text `已激活，无需邀请`; `'disabled'` → 【重新启用】(calls updateUser with `{status: 'active'}`).
- 【关闭】 / 【取消】 in any state closes the modal.

Modal heading: `邀请新用户`. Primary CTA: `生成邀请链接`. Active radio uses `bg-notion-tint-lavender` border + `text-notion-brand-purple-800`. Inactive radio uses `bg-notion-canvas border-notion-hairline-strong`.

The modal SHALL also render correctly as a mobile bottom sheet — the parent decides which container to wrap it in based on viewport.

#### Scenario: Successful invite shows URL with copy button
- **WHEN** the invite resolves to `{user, invite_url: "http://x/accept-invite?token=abc"}`
- **THEN** the URL is rendered in a `<code>` block AND a 【复制】 button (data-copy-btn) is visible

#### Scenario: 409 with active existing user shows disabled action
- **WHEN** the invite resolves to `{conflict: {status: 'active'}}`
- **THEN** the warning panel shows a button "已激活，无需重邀" with `disabled` attribute

#### Scenario: 409 with invited existing user offers resend
- **WHEN** the invite resolves to `{conflict: {status: 'invited', id: 'X'}}`
- **THEN** a 【重发邀请】 button is visible; clicking it calls `adminUsers.resendInvite('X')`

#### Scenario: Locked tokens on success state
- **WHEN** the invite resolves to `{user, invite_url: ...}`
- **THEN** success heading visible text matches `/✓ 邀请已生成/`; copy button classes match `/bg-notion-primary/`; visible text contains `7 天后过期`

### Requirement: DeleteUserModal component
`frontend/src/components/DeleteUserModal.vue` SHALL render a destructive confirmation:
- Red title "⚠ 永久删除用户" (text classes match `/text-notion-error/`).
- Sentence "<email> (<name>) 将被永久删除".
- Pink-tinted info box (classes match `/bg-notion-tint-rose/`) listing what gets deleted ("会一并删除：" with itemized list including private entries, notes, chat sessions / messages — Qdrant vectors included) AND what's preserved ("不会删除：" with knowledge files).
- Confirmation input requiring user to type the local part of the email (substring before `@`).
- 【取消】 (`bg-notion-canvas border-notion-hairline-strong`) and 【永久删除】 (`bg-notion-error text-notion-on-primary`, disabled until input matches the local part).

Verbatim labels: heading `⚠ 永久删除用户`; "会一并删除：" + "不会删除：" subheadings; cancel `取消`; destructive `永久删除`.

Submit calls `adminUsers.deleteUser(id)`. On success, modal closes and parent removes the user from view (the store action already handled removal). On error, modal shows inline error.

#### Scenario: Red delete button disabled until matching text typed
- **WHEN** the modal mounts for `linda@gmail.com`
- **THEN** the 【永久删除】 button has `disabled` attribute until the input value equals `linda` (case-sensitive)

#### Scenario: Successful delete closes modal
- **WHEN** the user types `linda` and clicks 【永久删除】 and the API returns 204
- **THEN** the modal emits `close` event and the parent stops rendering it

#### Scenario: Error renders inline, modal stays open
- **WHEN** the API returns 400 `{error: "user must be disabled before deletion"}`
- **THEN** the modal stays open and shows the error text near the buttons

#### Scenario: Locked tokens + heading text
- **WHEN** DeleteUserModal mounts for `linda@gmail.com`
- **THEN** heading classes match `/text-notion-error/` and visible text matches `/⚠ 永久删除用户/`; warning-box classes match `/bg-notion-tint-rose/`; destructive button classes match `/bg-notion-error/`

### Requirement: AppLayout 5th sidebar nav for admin users
`AppLayout.vue` SHALL conditionally render a 5th sidebar nav item `用户管理` (gear / settings icon) BELOW the existing 4 nav items, visible only when `auth.currentUser?.role === 'admin'`. Active state styling (`bg-notion-tint-lavender text-notion-brand-purple-800`) applies when the route starts with `/admin/`. Mobile bottom-tab is unchanged (still 5 items: 知识库 / 摄入 / 对话 / 私有数据 / 我); the admin link on mobile lives inside the `/me` view (already rendered conditionally on role from the core change).

#### Scenario: Admin sees 5 nav items in sidebar
- **WHEN** AppLayout renders with `auth.currentUser.role === 'admin'`
- **THEN** the desktop sidebar nav has 5 router-links (the existing 4 + "用户管理")

#### Scenario: Member sees 4 nav items in sidebar
- **WHEN** AppLayout renders with `auth.currentUser.role === 'member'`
- **THEN** the desktop sidebar nav has exactly 4 router-links (no 用户管理)

#### Scenario: Logged-out user sees 4 nav items in sidebar
- **WHEN** AppLayout renders with `auth.currentUser === null`
- **THEN** the desktop sidebar nav has 4 router-links (用户管理 hidden)

### Requirement: /admin/users route registration
`frontend/src/router/index.js` SHALL register a route at `/admin/users` mapped to `AdminUsersView`, with `meta.requiresAdmin: true` so the existing admin guard (already present from the core change) protects it.

#### Scenario: Direct URL navigation as admin works
- **WHEN** an admin pastes `/admin/users` in the URL bar
- **THEN** AdminUsersView renders (after the auth guard's fetchMe resolves)

#### Scenario: Direct URL navigation as member redirected
- **WHEN** a member pastes `/admin/users` in the URL bar
- **THEN** the router redirects to /chat
