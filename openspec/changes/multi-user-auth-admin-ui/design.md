## Context

`multi-user-auth-core` shipped the auth backbone + login/invite-via-CLI. This change adds the admin web UI on top so admins don't need `docker exec` for routine user management. Per the requirements doc and mocks, the UX shape is settled — this design doc captures the **decisions specific to the admin UI** + the cross-cutting decisions inherited from core.

Inherits unchanged from core: argon2id hashing, single users state machine, email canonicalization, per-request `status='active'` enforcement, Flask signed-cookie sessions, `SESSION_COOKIE_SECURE` env var, `/api/auth/*` endpoints, CLI invite tool (kept as fallback).

V1 scale assumption: ~5 family members. The admin UI prioritizes **safety** (can't accidentally lock yourself out, can't accidentally delete an active user) over **bulk efficiency** (no CSV import, no batch operations).

## Goals / Non-Goals

**Goals:**
- Admin can invite, list, change role, disable, re-enable, delete users via UI without leaving the browser.
- Each destructive action has a confirmation step proportional to its blast radius.
- Mobile equivalent is functional (bottom sheets instead of modals).
- The 409 duplicate-invite response is exposed in the UI as a recoverable, helpful error rather than a generic failure.

**Non-Goals:**
- Reset-password endpoint (admin disable + reinvite is the V1 recovery path; per the slim).
- Audit log (separate `auth-audit-log` change).
- Bulk operations (out of scope at family scale).
- Setting initial password directly during invite (dropped in slim).
- Removing the CLI tool (kept as emergency fallback).

## Decisions

### 1. Same `users` table, no schema changes

**Choice:** All admin endpoints operate on the existing `users` table from core. No migrations.

**Alternatives considered:**
- *Separate `admin_actions` log table:* would back an audit trail. Deferred — landing alongside the audit-log change.

**Why no migrations:** core's schema is already complete; this change is purely about exposing capabilities through endpoints + UI.

### 2. `@require_admin` extends `@require_auth`, not replaces

**Choice:** New decorator `@require_admin` first runs `@require_auth` (load user, check active), then checks `g.user.role == 'admin'`. Two-stage so the 401 vs 403 distinction is preserved (unauthenticated → 401; authenticated but not admin → 403).

**Alternatives considered:**
- *One combined decorator:* simpler but blurs 401 vs 403, which matters for axios's 401 interceptor (which redirects to /login; 403 should NOT redirect, just show "permission denied").

**Why two-stage:** keeps frontend behavior coherent. 401 → re-login; 403 → "wrong account, can't fix by re-login".

### 3. Delete requires `status='disabled'` first (two-step destruction)

**Choice:** `DELETE /api/admin/users/:id` returns 400 if the user is `'active'`. Admin must `PATCH ... status='disabled'` first, THEN call `DELETE`.

**Alternatives considered:**
- *Single-step delete with strong confirmation:* faster, but conflates "stop access" with "wipe data". A two-step path lets admin disable first to investigate before committing.
- *Soft delete only (mark deleted, never wipe):* doesn't free the email for reinvite. Hard delete is required if admin wants to re-add the same email later.

**Why two-step:** active users have data they're actively producing. If they're misbehaving, admin disables; if they leave permanently, admin deletes. Conflating loses information.

### 4. Type-to-confirm for delete (not just OK button)

**Choice:** Delete modal requires admin to type the first portion of the email (e.g., `linda` for `linda@gmail.com`) before the red 【永久删除】button enables.

**Alternatives considered:**
- *Single OK button with red color:* easy to misclick.
- *Type the FULL email:* tedious; admin already saw it.
- *Type a fixed string like "DELETE":* generic; doesn't tie the action to THIS specific user.

**Why type-the-localpart:** unique to the row + short enough to type without copy/paste + visually meaningful enough to prevent muscle-memory errors. Same pattern as Github / Linear.

### 5. Knowledge files stay on user delete (orphaned `user_id` is OK)

**Choice:** When a user is deleted, their `private_entries` / `notes` / `chat_sessions` are removed (with Qdrant cleanup). But files they ingested into the shared `knowledge` collection are KEPT. Their `user_id` in the `files` row becomes orphan-but-traceable.

**Alternatives considered:**
- *Cascade-delete knowledge files too:* loses content the rest of the household relies on. Bad.
- *Reattribute to admin:* changes ownership semantics; later filtering or auditing gets confusing.

**Why keep with orphan FK:** knowledge is shared content. Once contributed, it belongs to "the household", not the contributor. The orphan `user_id` is acceptable for audit ("who first uploaded this") and harmless because routes never filter knowledge by user_id.

### 6. 409 on duplicate invite, with context-aware UI

**Choice:** `POST /api/admin/users` with an existing email returns 409 + `{existing: {status, role}}`. Admin UI catches this and offers ONE follow-up action based on `existing.status`:
- `invited` → "重新发送邀请"
- `active` → disabled button "已激活、无需重邀"
- `disabled` → "重新启用"

**Alternatives considered:**
- *Generic 409 + "user exists" message:* admin has to manually figure out what to do.
- *Auto-resend invite if existing is invited:* could surprise admin. Better to ask.
- *Allow re-invite for active users (regenerates token):* dangerous — could lock out a legitimately-active user.

**Why context-aware:** turns a 409 into a productive next step. Reduces admin frustration.

### 7. Mobile uses bottom sheets, not modals

**Choice:** Invite + delete confirm on mobile slide up from the bottom (existing PrivateView pattern); on desktop they're centered modals.

**Alternatives considered:**
- *Modals on mobile too:* feels web-y, harder to reach top of viewport one-handed.
- *Full-page navigation (e.g., `/admin/users/invite` route):* more "native" but adds router config and back-button handling.

**Why bottom sheets:** consistent with the rest of the mobile app + thumb-reachable + dismiss via swipe-down or tap backdrop. Familiar pattern.

### 8. CLI tool stays in codebase post-ship

**Choice:** `python -m app.cli.invite_user` is not removed. CLAUDE.md is updated to position UI as primary path; CLI as emergency fallback.

**Alternatives considered:**
- *Remove CLI to reduce surface:* losing a working escape hatch. If admin breaks the UI somehow (JS error, browser issue, locked out from their own admin row via a bug), the CLI is the recovery path.

**Why keep:** ~30 lines of code, tests already exist from core, zero runtime cost when not invoked. Pure safety net.

## Risks / Trade-offs

- **R-01 — Admin demotes the only admin:** PATCH role from admin to member when they're the sole admin. Server-side guard returns 400 with `{error: "cannot demote the only admin"}`. UI also disables the button preemptively when `users.filter(role==='admin').length === 1` and target is self.
- **R-02 — Race condition: two admin tabs invite same email:** the UNIQUE constraint on `users.email` prevents the second insert; one returns 201, the other catches the constraint error and returns 409 with the existing row's status. Tests cover this in `test_admin_users_invite.py`.
- **R-03 — Admin disables themselves:** server-side guard rejects (400 + `{error: "cannot disable self"}`). UI's "停用" button is hidden on the self-row (the row already shows "不能改自己" placeholder).
- **R-04 — Delete cascade Qdrant failure mid-way:** if SQLite delete succeeds but Qdrant filter-delete fails, user is gone from app but their vectors remain in Qdrant. Not a security issue (no way to query them without the SQLite row) but a cleanup tax. Mitigation: Qdrant delete first (idempotent), THEN SQLite. Order swap reverses the failure mode to "vectors gone, SQLite row still there" which is more recoverable (retry the SQLite delete on next admin action).
- **R-05 — Mobile bottom sheet swipe-to-close discards in-progress invite:** acceptable; admin re-opens and types again. No autosave for V1.
- **R-06 — Admin UI reachable but `/api/admin/users` not yet deployed:** old image without admin endpoints, but new frontend trying to call them. Mitigation: build-and-push.sh ships api + frontend together with the same tag; NAS Pull/Apply atomically swaps both. The "frontend ahead of backend" mismatch only happens if someone manually pins different tags.

## Migration Plan

No data migration. Ship sequence:

1. Implement `@require_admin` middleware (extending `@require_auth`).
2. Implement 5 admin endpoints + tests.
3. Implement `user_service.delete_user_cascading(user_id)` with Qdrant filter-delete.
4. Implement `useAdminUsersStore` + `AdminUsersView` + `InviteUserModal` + `DeleteUserModal`.
5. Add 5th sidebar nav item to AppLayout (admin only).
6. Register `/admin/users` route + verify auth guard works.
7. Run all suites: backend pytest, frontend vitest, Playwright (new spec for the admin → invite → activate-as-member flow).
8. Live-test on dev stack: invite a fake user, accept as that user in another browser, verify the admin sees them as `active` after the flow.
9. Push image, NAS Pull → Apply.
10. Update CLAUDE.md: position UI as primary, CLI as emergency fallback.

**Rollback:** previous frontend image tag pinned in NAS docker-compose.yml. The new admin endpoints stay deployed (harmless if no UI calls them) but the UI hides the admin nav and AdminUsersView. CLI invite still works.

## UI Fidelity

Implementation MUST follow `docs/superpowers/specs/mocks/2026-05-09-multi-user-auth-mocks.html` §2 for all visual elements.

**Mock anchors used:**
- §2 `#admin-users` — AdminUsersView desktop table with row state coloring + invite modal 3 states + delete confirmation + mobile cards + bottom sheet invite

**Locked Notion design tokens (frontend tests assert via `wrapper.classes()`):**
- Hero band: `bg-notion-brand-navy` text `text-notion-on-dark`
- Table head: `bg-notion-surface-soft` with `border-notion-hairline-soft` row dividers
- Active status indicator: `text-notion-brand-green` with `bg-notion-brand-green` 6px circle
- Invited row tint: `bg-notion-tint-yellow` row + `text-notion-warning` accent + orange status dot
- Disabled row: `bg-notion-surface-soft` + `opacity-70` + `text-notion-stone` text + line-through email
- Admin role badge: `bg-notion-tint-lavender text-notion-brand-purple-800`
- Member role badge: `bg-notion-tint-gray text-notion-slate`
- Primary CTA (邀请用户 / 重发 / 启用): `bg-notion-primary text-notion-on-primary`
- Destructive CTA (永久删除): `bg-notion-error text-notion-on-primary` (red `#e03131`)
- Destructive secondary (删除 button in disabled row): `bg-notion-canvas border-notion-tint-rose text-notion-error`
- Delete modal warning box: `bg-notion-tint-rose border-notion-tint-rose`
- Status dots: green `bg-notion-brand-green` / orange `bg-notion-warning` / gray `bg-notion-steel`

**Verbatim text strings (frontend tests assert via `wrapper.text()`):**
- AdminUsersView heading: `用户管理`
- Count summary template: `<N> 个用户 · <X> admin · <Y> active · <Z> invited · <W> disabled`
- Self-row placeholder: `不能改自己`
- Per-state action button labels: `↑ admin` (promote), `↓ member` (demote), `停用`, `启用`, `重发`, `取消邀请`, `删除`
- Invite modal heading: `邀请新用户`; CTA `生成邀请链接`; cancel `取消`
- Invite success: `✓ 邀请已生成`; copy button `复制`; expiry hint `7 天后过期。如果对方没及时点，回列表"重发邀请"。`
- Invite 409 warning: `⚠ 该用户已存在`
- Invite 409 sub-action labels: `已激活，无需邀请` (disabled, status=active); `重发邀请` (status=invited); `重新启用` (status=disabled)
- Delete modal heading: `⚠ 永久删除用户`
- Delete modal "会一并删除：" + "不会删除：" headings (verbatim)
- Delete CTA: `永久删除` (red); cancel: `取消`
- Mobile invite bottom sheet: same form, drag handle bar at top

**Layout invariants:**
- Desktop table: 6 columns with widths `280px 1fr 90px 110px 130px 140px` (用户 / 姓名 / 角色 / 状态 / 最后登录 / 操作)
- Mobile cards: full width, vertical stack with status badge top-right of each card
- Invite is a centered modal on desktop (`max-w-[420px]`), bottom sheet on mobile (slides up from bottom with `rounded-t-xl` + drag handle)
- Delete modal on both: max-w-[480px] centered card on desktop; bottom sheet on mobile
- 5th sidebar nav item `用户管理` only visible when `auth.currentUser?.role === 'admin'`

The corresponding spec requirements in `specs/frontend-scaffold/spec.md` lock these tokens and strings. Tasks include MOCK + VISUAL DIFF sandwich tasks.

## Open Questions

None blocking. Soft items:

1. **Q-01:** Should admin see how many sessions a user has open? Useful for "I disabled them but they're still active in another tab" debugging. V1 = no (we don't track sessions explicitly with the signed-cookie model).
2. **Q-02:** Should the delete modal show a final summary count ("This will delete 3 entries, 7 notes, 2 chat sessions, 18 messages")? Useful but adds another query. Defer.
3. **Q-03:** When the only admin tries to delete the only other (member) user who happens to be themselves... wait, that can't happen since you can't delete self regardless. But: when admin tries to delete the only admin row (themselves), the guard "can't delete the only admin" blocks them too. Both guards together — admins are deletion-proof from themselves. Fine.
