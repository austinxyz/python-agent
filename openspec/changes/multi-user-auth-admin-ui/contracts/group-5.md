# Contract: Group 5 — AdminUsersView

## Spec

SHALL statements from `specs/frontend-scaffold/spec.md` satisfied by this group:

- On mount SHALL call `adminUsers.fetchUsers()`
- Hero band classes SHALL match `/bg-notion-brand-navy/` + `/text-notion-on-dark/`; heading text `用户管理`; CTA text `+ 邀请用户` with classes matching `/bg-notion-primary/`
- Self-row SHALL show `不能改自己` text, no action buttons
- `invited` row SHALL have `/bg-notion-tint-yellow/` background; `disabled` row SHALL have `/bg-notion-surface-soft/` + `/opacity-70/`
- Admin role badge classes SHALL match `/bg-notion-tint-lavender/` + `/text-notion-brand-purple-800/`; member badge `/bg-notion-tint-gray/` + `/text-notion-slate/`
- At 393px viewport: table element SHALL be hidden, card list SHALL be visible
- Demote-only-admin 【↓ member】 button SHALL have `disabled` attribute when only 1 admin in the users list

## Runtime

```
cd frontend && npm test -- tests/views/AdminUsersView.test.js
```

Expected: all assertions pass.

## Code

- `frontend/src/views/AdminUsersView.vue` — full admin user management view with hero band, desktop table, mobile cards, and modal integration
- Uses `<InviteUserModal>` and `<DeleteUserModal>` from group 4
- `useAdminUsersStore` for data; `useAuthStore` for `currentUser` self-row detection
- Design tokens: `bg-notion-brand-navy`, `text-notion-on-dark`, `bg-notion-primary`, `bg-notion-tint-yellow`, `bg-notion-surface-soft`, `opacity-70`, `bg-notion-tint-lavender`, `text-notion-brand-purple-800`, `bg-notion-tint-gray`, `text-notion-slate`
- R-01 (only-admin guard mirrored in UI): demote button disabled when `users.filter(u => u.role === 'admin').length <= 1`
- VISUAL DIFF verifies rendered output against `2026-05-09-multi-user-auth-mocks.html#admin-users`

## Threshold

70
