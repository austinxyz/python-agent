# Contract: Group 1 — @require_admin middleware

## Spec

SHALL statements from `specs/multi-user-auth/spec.md` satisfied by this group:

- `@require_admin` SHALL return 401 (clearing session cookie) when the request is unauthenticated
- `@require_admin` SHALL return 403 (preserving session cookie) when authenticated but `role != 'admin'`
- `@require_admin` SHALL set `g.user` and proceed (200) when `role == 'admin'` and `status == 'active'`

## Runtime

```
cd backend && pytest tests/test_middleware_require_admin.py -v
```

Expected: all scenarios pass (4 test cases covering unauthenticated→401, member→403, admin→200+g.user, cookie behaviour).

## Code

Two-stage decorator pattern in `backend/app/middleware.py`:
- Stage 1: `_validate_session()` — if None → `_clear_session_and_401()` (session cleared, 401)
- Stage 2: role check — if `g.user.role != 'admin'` → 403, cookie preserved (no `session.clear()`)
- Design decision §2 from design.md: the 401 vs 403 split matters because the frontend axios 401 interceptor redirects to /login; 403 must NOT redirect (just show "permission denied").

## Threshold

80
