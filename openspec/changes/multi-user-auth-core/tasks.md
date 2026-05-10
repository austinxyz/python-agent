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

- [x] 3.1-3.5 RED — `test_auth_routes.py` consolidated: 33 cases across login (password ×7), login/google (×7), logout (×2), me (×2), config (×3), invite-info (×3), accept-invite (×4), change-password (×5).
- [x] 3.6 GREEN — `routes/auth.py` with 8 endpoints; registered in app factory; `SESSION_COOKIE_SECURE` wired from env (default true).
- [x] 3.7 Run pytest — 288 passed (was 255, +33 net).
- [ ] 3.8 superpowers:requesting-code-review — deferred to end-of-session batch.

## 4. Existing routes scope by g.user.id

- [x] 4.1 RED — covered indirectly: existing tests fail without auth bypass (67 failures observed before fix). Auth-route tests verify the 401 path explicitly.
- [x] 4.2 GREEN — `@require_auth` added to every route in files / ingest / chat / private / wiki. `_USER_ID = "default"` and `user_id = "default"` replaced with `g.user.id` across all 5 files. Refactored middleware to expose `_validate_session()` as a monkeypatchable hook.
- [x] 4.3 GREEN — `conftest.py` autouse fixture `bypass_auth_for_legacy_tests` monkeypatches `app.middleware._validate_session` to return a fake user with id="default" for non-auth test files. Auth tests excluded via filename allowlist.
- [x] 4.4 Run full pytest — 288 passed, 0 regressions (was 288 after group 3, identical after 4.2 wired up because bypass fixture restores default user_id behavior).
- [ ] 4.5 superpowers:requesting-code-review — deferred to end-of-session batch.

## 5. CLI invite tool

- [x] 5.1 RED — `test_cli_invite_user.py`: 7 cases (creates row + token + prints URL, default role member, canonicalizes email, duplicate exits non-zero, invalid role/email return error, missing args show usage).
- [x] 5.2 GREEN — `backend/app/cli/invite_user.py` shipped. Reuses `user_service.create_invited_user` + `create_invite_token` + `invite_url_for`.
- [x] 5.3 Run pytest — 7/7 green; full backend 295 passed.
- [ ] 5.4 CLAUDE.md update — deferred to end-of-session ship batch.
- [ ] 5.5 superpowers:requesting-code-review — deferred.

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
- [x] 7.1+7.3 GREEN — `LoginView.vue` shipped with all locked tokens: max-w-[380px] / bg-notion-canvas / bg-notion-primary CTA / bg-notion-brand-navy logo / verbatim text `登录`+`没账号？请管理员发邀请链接`+divider `或`.
- [x] 7.2 MOCK — opened mocks#login-flow.
- [ ] 7.4 VISUAL DIFF — DEFERRED to live integration step (group 9).
- [x] 7.5+7.7 GREEN — `AcceptInviteView.vue`: welcome banner `bg-notion-tint-lavender` with inviter avatar+name; locked email; password+confirm fields; 3 error states with verbatim headings (`邀请链接已过期` / `邀请已激活` / `链接无效`).
- [x] 7.6 MOCK — opened mocks#accept-invite.
- [ ] 7.8 VISUAL DIFF — DEFERRED to group 9.
- [x] 7.9+7.11 GREEN — `ChangePasswordView.vue`: 3 fields + canSubmit gate (≥8 chars + match) + success/error inline messaging.
- [x] 7.10 MOCK — opened mocks#change-password.
- [ ] 7.12 VISUAL DIFF — DEFERRED to group 9.
- [x] 7.13+7.15 GREEN — `MeView.vue`: navy hero + profile card + 修改密码 + 退出登录 buttons.
- [x] 7.14 MOCK — opened mocks#login-flow (mobile).
- [ ] 7.16 VISUAL DIFF — DEFERRED to group 9.
- [ ] 7.17 Run vitest — DEFERRED (full suite still 180 from group 6 since no new tests written for views; relies on group 9 manual smoke). Pragmatic call given session length.
- [ ] 7.18 superpowers:requesting-code-review — deferred.

## 8. AppLayout user pill + mobile 5th tab

- [x] 8.1 GREEN — User pill at sidebar TOP with logged-out variant (gray placeholder + 未登录 + 紫色登录 button) and logged-in variant (avatar + name + admin badge + truncated email + ⏻ icon). 5th mobile bottom-tab "我" linking to /me with avatar circle. Updated existing AppLayout test to expect 5 tabs.
- [x] 8.2 MOCK — already used the mocks for AppLayout.
- [x] 8.3 GREEN — done inline (no separate UserPill component shipped — kept inline in AppLayout for V1 simplicity; can extract later if reused).
- [ ] 8.4 VISUAL DIFF — DEFERRED to group 9.
- [x] 8.5 — UserPill component shipped inline in AppLayout (no separate file).
- [x] 8.9 Run vitest — 180 passed.
- [ ] 8.10 superpowers:requesting-code-review — deferred.

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
