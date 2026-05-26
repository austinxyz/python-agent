# Contract: Group 6 — AppLayout 5th sidebar item + router registration

## Spec

SHALL statements from `specs/frontend-scaffold/spec.md` satisfied by this group:

- AppLayout SHALL render 5th sidebar nav item `用户管理` only when `auth.currentUser?.role === 'admin'`; member and logged-out users see exactly 4 items
- Active state on `/admin/*` routes SHALL use classes matching `/bg-notion-tint-lavender/` + `/text-notion-brand-purple-800/`
- `/admin/users` route SHALL be registered with `meta.requiresAdmin: true`; member navigating there SHALL be redirected to `/chat`; unauthenticated to `/login?redirect=/admin/users`

## Runtime

```
cd frontend && npm test -- tests/components/AppLayout.test.js tests/router-admin-route.test.js
```

Expected: all assertions pass.

## Code

- `frontend/src/components/AppLayout.vue` — add conditional 5th `<router-link to="/admin/users">` with `v-if="auth.currentUser?.role === 'admin'"` in sidebar nav; active-state classes `bg-notion-tint-lavender text-notion-brand-purple-800`
- `frontend/src/router/index.js` — register `/admin/users` route pointing to `AdminUsersView`, with `meta.requiresAdmin: true`; verify that the existing `beforeEach` guard already handles admin-only redirect
- Design token locked: `bg-notion-tint-lavender`, `text-notion-brand-purple-800`

## Threshold

70
