# Contract: Group 8 — E2E for admin → member flow

## Spec

SHALL statements:
- E2E SHALL cover: admin login → /admin/users → invite new user → accept invite as new user (separate browser context) → admin sees new user as `active`
- E2E SHALL cover: admin PATCH (disable a user, then re-enable)
- E2E SHALL cover: admin DELETE with type-to-confirm (disable user first, then delete with matching localpart input)

## Runtime

```
cd frontend && npm run e2e -- --grep "admin-flow"
```

Expected: all admin-flow scenarios green.

## Code

- `frontend/e2e/admin-flow.spec.ts`: new file with 3 test scenarios
- Uses auth fixtures from core (`auth-fixture.ts`) for admin login
- New browser context for accept-invite flow (separate storage state)
- `__e2e_*` prefix for test users; `afterEach` cleanup even on failure
- Type-to-confirm: fills localpart of email, asserts delete button enables

## Threshold

70
