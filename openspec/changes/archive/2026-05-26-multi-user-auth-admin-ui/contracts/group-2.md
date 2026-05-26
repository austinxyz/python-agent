# Contract: Group 2 — Admin user CRUD endpoints

## Spec

SHALL statements from `specs/multi-user-auth/spec.md` satisfied by this group:

- GET /api/admin/users SHALL return all users sorted `invited_at DESC` with computed `has_google`, `has_password`, `invited_by_email` fields; 401 without auth; 403 as member
- POST /api/admin/users SHALL return 201 + `{user, invite_url}` for new email; 409 + `{error: "user already exists", existing: {id, email, status, role}}` for duplicate (after `.strip().lower()` canonicalization)
- PATCH /api/admin/users/:id SHALL reject self-role-change (400 "cannot change own role"), self-disable (400 "cannot disable self"), only-admin-demote (400 "cannot demote the only admin"), invalid status enum with 400; return 200 + updated user on valid change
- DELETE /api/admin/users/:id SHALL reject active user (400 "user must be disabled before deletion"), self (400 "cannot delete self"), only-admin (400); cascade-delete `private_entries` / `notes` / `chat_sessions` / `chat_messages` + Qdrant filter-delete on `private` collection by `user_id`; preserve `files` table rows; Qdrant filter-delete runs BEFORE SQLite delete
- POST /api/admin/users/:id/resend-invite SHALL return 400 + `{error: "user is not in invited state"}` for non-invited status; 200 + `{invite_url}` with old token marked used and new token created for `status='invited'`

## Runtime

```
cd backend && pytest tests/test_admin_users_list.py tests/test_admin_users_invite.py tests/test_admin_users_patch.py tests/test_admin_users_delete.py tests/test_admin_users_resend_invite.py -v
```

Expected: all scenarios pass, full suite no regressions.

## Code

- `backend/app/routes/admin_users.py` — new blueprint with 5 endpoints, all `@require_admin`
- `backend/app/services/user_service.py` — extended with `delete_user_cascading(user_id)` (Qdrant filter-delete first, then SQLite cascade)
- Design decision §3: delete requires `status='disabled'` first (two-step destruction)
- Design decision §5: knowledge files preserved on delete (orphan `user_id` acceptable for audit)
- Design decision §6: 409 returns `existing` context for UI to branch on
- R-04 (design.md §Risks): Qdrant filter-delete BEFORE SQLite — on partial failure, recovery state is "vectors gone, SQLite row still there" (retryable) rather than the inverse (unrecoverable)
- Security-critical: all endpoints `@require_admin`; PATCH self-protection rules are the primary server-side defense against privilege escalation

## Threshold

80
