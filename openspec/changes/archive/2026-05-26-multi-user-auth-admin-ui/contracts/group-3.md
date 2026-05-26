# Contract: Group 3 — useAdminUsersStore

## Spec

SHALL statements from `specs/frontend-scaffold/spec.md` satisfied by this group:

- `fetchUsers()` SHALL call GET /api/admin/users and populate `store.users`
- `inviteUser(email, role)` SHALL POST to /api/admin/users; on 409 SHALL return `{conflict: existing}` (not throw); on success SHALL push the new user into `store.users`
- `deleteUser(id)` SHALL call DELETE /api/admin/users/:id; on success SHALL remove the matching user from `store.users`
- `updateUser(id, patch)` SHALL call PATCH /api/admin/users/:id; on success SHALL update the matching row in `store.users` in place
- `resendInvite(id)` SHALL call POST /api/admin/users/:id/resend-invite and return `{invite_url}`
- All actions SHALL call the correct API endpoints with the correct HTTP methods and request bodies
- Axios instance SHALL be injected as a dependency for testability (same pattern as `auth.js` / `chat.js`)

## Runtime

```
cd frontend && npm test -- tests/stores/adminUsers.test.js
```

Expected: all assertions pass.

## Code

- `frontend/src/stores/adminUsers.js` — Pinia store with `fetchUsers`, `inviteUser`, `deleteUser`, `updateUser`, `resendInvite`
- 409 catch-and-return (not rethrow) is critical for the InviteUserModal 3-state flow (invited/active/disabled follow-up action)
- Axios instance injected for testability — same pattern as `auth.js` / `chat.js`
- `store.error` remains null on expected 409 conflicts (conflict is not an error state, it's a branching point)

## Threshold

80
