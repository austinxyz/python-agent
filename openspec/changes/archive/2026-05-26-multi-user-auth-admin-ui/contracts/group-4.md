# Contract: Group 4 — InviteUserModal + DeleteUserModal

## Spec

SHALL statements from `specs/frontend-scaffold/spec.md` satisfied by this group:

- InviteUserModal heading text SHALL be `邀请新用户`; success heading SHALL contain `✓ 邀请已生成`; copy button SHALL have `data-copy-btn` attribute and classes matching `/bg-notion-primary/`; hint text SHALL contain `7 天后过期`
- On 409 `status='active'`: a button with text `已激活，无需邀请` SHALL have `disabled` attribute
- On 409 `status='invited'`: a `【重发邀请】` button SHALL be visible and SHALL call `adminUsers.resendInvite(id)` when clicked
- On 409 `status='disabled'`: a `【重新启用】` button SHALL call `adminUsers.updateUser(id, {status:'active'})` when clicked
- DeleteUserModal heading text SHALL match `/⚠ 永久删除用户/`; heading classes SHALL match `/text-notion-error/`; warning box classes SHALL match `/bg-notion-tint-rose/`; destructive CTA classes SHALL match `/bg-notion-error/`
- DeleteUserModal destructive CTA SHALL be disabled until input value equals local part of the email (substring before `@`)

## Runtime

```
cd frontend && npm test -- tests/components/InviteUserModal.test.js tests/components/DeleteUserModal.test.js
```

Expected: all assertions pass.

## Code

- `frontend/src/components/InviteUserModal.vue` — 3-state modal: form / success / conflict
- `frontend/src/components/DeleteUserModal.vue` — type-to-confirm destructive modal
- Design §6 (409 context-aware sub-actions), §4 (type-to-confirm localpart)
- Design tokens locked: `bg-notion-primary`, `text-notion-error`, `bg-notion-tint-rose`, `bg-notion-error`
- VISUAL DIFF tasks verify rendered output against `2026-05-09-multi-user-auth-mocks.html#admin-users`

## Threshold

70
