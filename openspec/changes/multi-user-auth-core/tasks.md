## 1. Schema + bootstrap migration

- [x] 1.1 RED — `tests/test_users_schema.py`: 8 cases on users + invite_tokens shape, constraints, FK cascade, idempotency.
- [x] 1.2 GREEN — appended `users` + `invite_tokens` to schema.sql with indexes (idx_users_email/status, partial idx_users_google_sub, idx_invite_tokens_user_id).
- [x] 1.3 RED — `tests/test_email_canonicalization.py`: 5 cases — lower / strip / both / already-canonical / empty.
- [x] 1.4 GREEN — `auth_service.canonicalize_email()` shipped.
- [x] 1.5 RED — `tests/test_bootstrap_migration.py`: 7 cases — admin creation + invite token + URL stdout + idempotent + email canonicalization + 4-table data rewrite + Qdrant scroll called.
- [x] 1.6 GREEN — `user_service.py` shipped with `bootstrap_initial_admin`, `migrate_default_user_data`, Qdrant scroll-and-set_payload migration.
- [x] 1.7 Run pytest — all 20 group-1 tests green.
- [ ] 1.8 Run superpowers:requesting-code-review on the diff for group 1; deferred to end-of-session batch.

## 2. Auth service + middleware

- [x] 2.1 RED — 7 password test cases (argon2id prefix, unique salt, verify happy/wrong/empty/malformed/None).
- [x] 2.2 GREEN — `auth_service.hash_password/verify_password` using argon2-cffi PasswordHasher defaults. argon2-cffi + google-auth added to requirements.txt.
- [x] 2.3 RED — 5 Google verify tests (requires token, requires audience env, env-vs-explicit audience, sanitized error, fake verify monkeypatch).
- [x] 2.4 GREEN — `auth_service.verify_google_token` wrapping `google.oauth2.id_token.verify_oauth2_token` with safe error wrapping.
- [x] 2.5 RED — 5 middleware cases (no session / unknown user / active passes + g.user / disabled / invited all 401).
- [x] 2.6 GREEN — `backend/app/middleware.py` with @require_auth.
- [x] 2.7 Run pytest — 255 passed, 1 skipped (was 218 pre-change; +37 net).
- [ ] 2.8 superpowers:requesting-code-review — deferred to end-of-session batch.

## 3. Auth routes

- [ ] 3.1 RED — `tests/test_auth_routes_login_password.py`: 401 for nonexistent / wrong-password / disabled / no-password-hash users (all same body `{"error":"invalid credentials"}`); 200 + session cookie + user object on success; updates last_login_at.
- [ ] 3.2 RED — `tests/test_auth_routes_login_google.py`: 6 cases per the spec table (not invited / disabled / invited→activate / active+null sub→link / active+matching sub→refresh / active+mismatched sub→403). Mock `auth_service.verify_google_token`.
- [ ] 3.3 RED — `tests/test_auth_routes_logout_me_config.py`: logout 204 + clears session; me 200 with user / 401 without; config returns has_google + client_id from env.
- [ ] 3.4 RED — `tests/test_auth_routes_invite_accept.py`: `GET /api/auth/invite/<token>` returns user + valid/expired flags; `POST /api/auth/accept-invite` 200 on valid token + ≥8 char password (sets password_hash, status=active, marks token used, opens session); 400 on short password; 410 on expired or used token.
- [ ] 3.5 RED — `tests/test_auth_routes_change_password.py`: 200 on correct old + valid new (different); 401 on wrong old; 400 on same-as-old; 400 on short new; 401 without auth.
- [ ] 3.6 GREEN — `backend/app/routes/auth.py` implementing all 8 endpoints. Register the blueprint in app factory. SESSION_COOKIE_SECURE wired through Flask config from env.
- [ ] 3.7 Run pytest — green.
- [ ] 3.8 Run superpowers:requesting-code-review on the diff for group 3.

## 4. Existing routes scope by g.user.id

- [ ] 4.1 RED — extend existing `tests/test_files.py`, `test_chat_routes.py`, `test_private_entries.py`, `test_private_notes.py`, `test_ingest_pipeline.py`, `test_wiki_routes.py`: every endpoint returns 401 without an auth fixture; with the fixture, the handler uses `g.user.id` (assert via inspecting the SQL or Qdrant call args, not by hardcoded `"default"`).
- [ ] 4.2 GREEN — add `@require_auth` to every route in `files.py`, `ingest.py`, `chat.py`, `private.py`, `wiki.py`. Replace each `user_id = "default"` with `user_id = g.user.id` (no other behavior change).
- [ ] 4.3 GREEN — add a shared pytest fixture (e.g., `authenticated_client`) that creates an active user + opens a session for tests that previously assumed default user.
- [ ] 4.4 Run full pytest — should be 218 pre-change + however many new tests landed. Zero regressions; existing behavior preserved per-user.
- [ ] 4.5 Run superpowers:requesting-code-review on the diff for group 4.

## 5. CLI invite tool

- [ ] 5.1 RED — `tests/test_cli_invite_user.py`: invoking the module with new email creates row + token + prints URL to stdout; with existing email returns non-zero exit + clear stderr message; canonicalizes email; respects role argument.
- [ ] 5.2 GREEN — `backend/app/cli/invite_user.py` exposing `python -m app.cli.invite_user <email> [role]` via `if __name__ == '__main__':`. Reuses the same `user_service.create_invite(email, role)` that the future admin route will call.
- [ ] 5.3 Run pytest — green.
- [ ] 5.4 Document in CLAUDE.md Pitfalls: "to invite users in the multi-user-auth-core era, run `docker exec -it python-agent-api python -m app.cli.invite_user <email> [role]` and copy the printed URL".
- [ ] 5.5 Run superpowers:requesting-code-review on the diff for group 5.

## 6. Frontend store + axios + router

- [ ] 6.1 RED — `frontend/tests/stores/auth.test.js`: store actions call expected endpoints with right bodies; `fetchMe` populates currentUser on 200, sets null on 401; `loginWithPassword` calls `/api/auth/login`; `loginWithGoogle` calls `/api/auth/login/google`; `acceptInvite` / `changePassword` / `logout` route correctly.
- [ ] 6.2 GREEN — `frontend/src/stores/auth.js`. Inject axios instance for testability (existing pattern from chat.js).
- [ ] 6.3 RED — `frontend/tests/api-401-interceptor.test.js`: a 401 from `/api/private/entries` clears `auth.currentUser` and pushes `/login?redirect=/private`; a 401 from `/api/auth/login` does NOT trigger redirect (the action handles it).
- [ ] 6.4 GREEN — extend `frontend/src/api/index.js` with the response interceptor.
- [ ] 6.5 RED — `frontend/tests/router-guard.test.js`: navigation to `/private` while logged-out → redirect to `/login?redirect=/private`; `/login` and `/accept-invite` reachable without auth; `/` redirects to `/chat`; logged-in user navigating to `/admin/anything` (none exist yet) is redirected to `/chat` per the future-proof admin guard.
- [ ] 6.6 GREEN — `frontend/src/router/index.js` adds `/login`, `/accept-invite`, `/change-password`, `/me`; root redirect changes to `/chat`; global beforeEach with auth + admin checks.
- [ ] 6.7 Run vitest — full suite green (existing 169 + new tests).
- [ ] 6.8 Run superpowers:requesting-code-review on the diff for group 6.

## 7. Frontend views (Login / AcceptInvite / ChangePassword / Me)

- [ ] 7.1 RED — `frontend/tests/views/LoginView.test.js`: form submits → `auth.loginWithPassword`; GSI button conditional on `config.has_google` AND host (mock `window.location` for tests); error message renders on rejected promise; successful login navigates per ?redirect query. **Per spec, also assert `wrapper.classes()` includes `bg-notion-canvas` + `max-w-[380px]` on root, `bg-notion-primary` on CTA; assert `wrapper.text()` contains `登录` + `没账号？请管理员发邀请链接`.**
- [ ] 7.2 MOCK — open `docs/superpowers/specs/mocks/2026-05-09-multi-user-auth-mocks.html#login-flow`. Note: navy hero band `bg-notion-brand-navy`, card `max-w-[380px] bg-notion-canvas border-notion-hairline`, primary CTA `bg-notion-primary`, divider literal `或`, GSI button outline style.
- [ ] 7.3 GREEN — `frontend/src/views/LoginView.vue`. Renders inside AppLayout (sidebar visible).
- [ ] 7.4 VISUAL DIFF — `npm run dev:up`, navigate to `/login` in browser, eyeball against mock §1; fix any drift in tokens / spacing / text BEFORE the group review.
- [ ] 7.5 RED — `frontend/tests/views/AcceptInviteView.test.js`: mount with `?token=abc` mocks `/api/auth/invite/abc` (valid / expired / used / invalid); valid case shows welcome banner classes match `bg-notion-tint-lavender`; visible text contains `设置你的密码` and `完成注册并登录`; 3 error states each show their literal heading; submit calls `auth.acceptInvite` and pushes /chat on success.
- [ ] 7.6 MOCK — open `mocks doc#accept-invite`. Note: welcome banner `bg-notion-tint-lavender`, locked email field with `disabled` attribute, error states use `text-notion-warning` (expired) / `text-notion-brand-green` (used) / `text-notion-error` (invalid).
- [ ] 7.7 GREEN — `frontend/src/views/AcceptInviteView.vue`.
- [ ] 7.8 VISUAL DIFF — navigate to `/accept-invite?token=...` (use a real token from CLI invite); manually trip the 3 error states by submitting bad/expired/used tokens; fix drift.
- [ ] 7.9 RED — `frontend/tests/views/ChangePasswordView.test.js`: 3 fields render; submit calls `auth.changePassword`; mismatch confirm prevents submit; old-password-wrong renders inline error with `text-notion-error`. Assert visible text contains `修改密码` + `保存`.
- [ ] 7.10 MOCK — open `mocks doc#change-password`. Simple 3-field form, primary CTA, secondary cancel.
- [ ] 7.11 GREEN — `frontend/src/views/ChangePasswordView.vue`.
- [ ] 7.12 VISUAL DIFF — navigate to `/change-password` while logged in; submit wrong old password; verify inline error styling.
- [ ] 7.13 RED — `frontend/tests/views/MeView.test.js`: shows current user info; "修改密码" link only when `password_hash` is set; "退出登录" button has classes matching `border-notion-tint-rose` (hover) and calls `auth.logout` + goes to /login. Visible text contains `修改密码` + `退出登录`.
- [ ] 7.14 MOCK — open `mocks doc#login-flow` (mobile section showing "我" tab). Profile card pattern + buttons stacked.
- [ ] 7.15 GREEN — `frontend/src/views/MeView.vue`.
- [ ] 7.16 VISUAL DIFF — at mobile viewport (Chrome DevTools iPhone 14), tap "我" tab from `/chat`; eyeball.
- [ ] 7.17 Run vitest — full suite green.
- [ ] 7.18 Run superpowers:requesting-code-review on the diff for group 7.

## 8. AppLayout user pill + mobile 5th tab

- [ ] 8.1 RED — `frontend/tests/components/AppLayout.test.js` extension: at desktop viewport with `auth.currentUser=null`, sidebar top has `data-user-pill` element with classes `bg-notion-canvas` + visible text `未登录` + `登录` button (classes `bg-notion-primary`). With admin user, pill shows admin badge with classes matching `bg-notion-tint-lavender` AND `text-notion-brand-purple-800`, visible text includes `admin`. At mobile viewport, `[data-bottom-tabs]` has 5 children; last one is "我" linking to `/me`.
- [ ] 8.2 MOCK — open `mocks doc#login-flow` desktop sidebar variant (both logged-out and logged-in panels). Note: pill at TOP of sidebar (above logo, NOT bottom); 28×28 avatar circle; logout icon `⏻` not text.
- [ ] 8.3 GREEN — `frontend/src/components/AppLayout.vue`: insert `<UserPill>` at top of desktop sidebar (above the logo block); add 5th `<router-link to="/me">` to bottom-tab nav.
- [ ] 8.4 VISUAL DIFF — at desktop viewport, log out and log back in; verify pill state transitions look right; verify mobile bottom-tab has 5 tabs.
- [ ] 8.5 RED — `frontend/tests/components/UserPill.test.js`: avatar uses Google picture if present, else first letter of email on hash-derived background color; role badge shows "admin" with `bg-notion-tint-lavender` only when role='admin' (member has no badge); logout icon button has title attribute `退出` and dispatches `auth.logout`.
- [ ] 8.6 MOCK — same anchor as 8.2; zoom in on the pill structure (avatar, name, badge, email truncated, ⏻).
- [ ] 8.7 GREEN — `frontend/src/components/UserPill.vue` (small standalone component, ~80 lines).
- [ ] 8.8 VISUAL DIFF — same as 8.4 (already covered when integrated into AppLayout).
- [ ] 8.9 Run vitest — full suite green.
- [ ] 8.10 Run superpowers:requesting-code-review on the diff for group 8.

## 9. Live integration

- [ ] 9.1 Bring up dev stack with `npm run dev:up`. Verify in browser at `localhost:3000`: bootstrap migration runs (check `docker logs`), root URL `/` redirects to `/chat` then `/login` since no session. Submit invite URL from logs to verify the full /accept-invite → /chat flow with admin email.
- [ ] 9.2 In another browser profile, run `docker exec -it python-agent-dev-api-1 python -m app.cli.invite_user testuser@example.com member`. Use the printed URL → /accept-invite → set password → land on /chat. Verify that user's `/private` is empty (isolation works).
- [ ] 9.3 As admin in browser 1, ingest a knowledge file. As member in browser 2, verify the file is visible (knowledge is shared).
- [ ] 9.4 As member, create a private entry. As admin, verify it does NOT appear under admin's `/private`.
- [ ] 9.5 If `GOOGLE_CLIENT_ID` is configured, sign in with Google as admin (email matches admin row) and verify auto-link sets `google_sub`. Sign out, sign in again with password, verify still works (both methods coexist).

## 10. E2E updates

- [ ] 10.1 RED — existing E2E specs (`chat.spec.ts`, `wiki.spec.ts`, `private-*.spec.ts`, `ingest.spec.ts`, `mobile.spec.ts`) all fail post-change because they assume no login. Decide: either add a pre-test login step or mock the session cookie. Mock approach is faster and matches existing API-mock pattern.
- [ ] 10.2 GREEN — add a Playwright fixture (`e2e/auth-fixture.ts`) that, before each test, mocks `/api/auth/me` to return a fixed test user and stores a session cookie. Use it as the default fixture for all existing specs.
- [ ] 10.3 NEW — `e2e/auth.spec.ts`: full happy-path flow without the auth-fixture: visit `/wiki` while logged-out → redirect to /login → submit valid credentials (mocked `/api/auth/login`) → land at /wiki. Logout → back at /login. AcceptInviteView with mocked token endpoint.
- [ ] 10.4 Run `npm run e2e` — full suite (desktop + mobile) green.
- [ ] 10.5 Run superpowers:requesting-code-review on the e2e diff.

## 11. Verification & ship

- [ ] 11.1 Run full backend pytest — should be 218 + new (~80 net) all green.
- [ ] 11.2 Run full frontend vitest — should be 169 + new (~50 net) all green.
- [ ] 11.3 Run full Playwright — desktop + mobile + new auth spec all green.
- [ ] 11.4 Manual smoke on dev stack: full flow per group 9.
- [ ] 11.5 Run superpowers:verification-before-completion: tests green; no console.log; spec ↔ implementation consistent; CLAUDE.md updated.
- [ ] 11.6 Final superpowers:requesting-code-review on the entire change diff.

## Ship

- [ ] S.1 `./scripts/build-and-push.sh` — pushes new api + frontend images.
- [ ] S.2 Update NAS `.env` (UGOS file manager): add `INITIAL_ADMIN_EMAIL=austin.xyz@gmail.com`, `SESSION_COOKIE_SECURE=false`. Optional: `GOOGLE_CLIENT_ID=...` if you set up an OAuth client (works only in localhost dev anyway).
- [ ] S.3 NAS UGOS Docker app → Project python-agent → Pull → Apply.
- [ ] S.4 In a browser at `http://10.0.0.20:8910`: should redirect to `/login`. Read `docker logs` (via UGOS UI's "logs" button on the api container) to find the bootstrap invite URL. Open URL, set admin password, verify all 85 files / 30 entries / 14 notes / 18 messages visible under your account.
- [ ] S.5 Use CLI to invite one family member; verify their flow works on a different device / browser.
- [ ] S.6 git add / commit with `feat: multi-user-auth-core` style message.
- [ ] S.7 git push.
- [ ] S.8 Update `docs/log/<date>.md` with the deployment summary.
- [ ] S.9 `openspec archive multi-user-auth-core` to merge requirements into the affected capability specs.
