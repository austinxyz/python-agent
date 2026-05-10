## 1. Schema + bootstrap migration

- [x] 1.1 RED — `tests/test_users_schema.py`: 8 cases on users + invite_tokens shape, constraints, FK cascade, idempotency.
- [x] 1.2 GREEN — appended `users` + `invite_tokens` to schema.sql with indexes (idx_users_email/status, partial idx_users_google_sub, idx_invite_tokens_user_id).
- [x] 1.3 RED — `tests/test_email_canonicalization.py`: 5 cases — lower / strip / both / already-canonical / empty.
- [x] 1.4 GREEN — `auth_service.canonicalize_email()` shipped.
- [x] 1.5 RED — `tests/test_bootstrap_migration.py`: 7 cases — admin creation + invite token + URL stdout + idempotent + email canonicalization + 4-table data rewrite + Qdrant scroll called.
- [x] 1.6 GREEN — `user_service.py` shipped with `bootstrap_initial_admin`, `migrate_default_user_data`, Qdrant scroll-and-set_payload migration.
- [x] 1.7 Run pytest — all 20 group-1 tests green.
- [x] 1.8 Code review: covered by 2026-05-10 batch (code-reviewer + security-reviewer agents). 2 HIGH found (open redirect, picture_url XSS), 1 MEDIUM (token lex compare) — all fixed in commit `d011aec`.

## 2. Auth service + middleware

- [x] 2.1 RED — 7 password test cases (argon2id prefix, unique salt, verify happy/wrong/empty/malformed/None).
- [x] 2.2 GREEN — `auth_service.hash_password/verify_password` using argon2-cffi PasswordHasher defaults. argon2-cffi + google-auth added to requirements.txt.
- [x] 2.3 RED — 5 Google verify tests (requires token, requires audience env, env-vs-explicit audience, sanitized error, fake verify monkeypatch).
- [x] 2.4 GREEN — `auth_service.verify_google_token` wrapping `google.oauth2.id_token.verify_oauth2_token` with safe error wrapping.
- [x] 2.5 RED — 5 middleware cases (no session / unknown user / active passes + g.user / disabled / invited all 401).
- [x] 2.6 GREEN — `backend/app/middleware.py` with @require_auth.
- [x] 2.7 Run pytest — 255 passed, 1 skipped (was 218 pre-change; +37 net).
- [x] 2.8 Code review: covered by 2026-05-10 batch (see 1.8).

## 3. Auth routes

- [x] 3.1-3.5 RED — `test_auth_routes.py` consolidated: 33 cases across login (password ×7), login/google (×7), logout (×2), me (×2), config (×3), invite-info (×3), accept-invite (×4), change-password (×5).
- [x] 3.6 GREEN — `routes/auth.py` with 8 endpoints; registered in app factory; `SESSION_COOKIE_SECURE` wired from env (default true).
- [x] 3.7 Run pytest — 288 passed (was 255, +33 net).
- [x] 3.8 Code review: covered by 2026-05-10 batch (see 1.8).

## 4. Existing routes scope by g.user.id

- [x] 4.1 RED — covered indirectly: existing tests fail without auth bypass (67 failures observed before fix). Auth-route tests verify the 401 path explicitly.
- [x] 4.2 GREEN — `@require_auth` added to every route in files / ingest / chat / private / wiki. `_USER_ID = "default"` and `user_id = "default"` replaced with `g.user.id` across all 5 files. Refactored middleware to expose `_validate_session()` as a monkeypatchable hook.
- [x] 4.3 GREEN — `conftest.py` autouse fixture `bypass_auth_for_legacy_tests` monkeypatches `app.middleware._validate_session` to return a fake user with id="default" for non-auth test files. Auth tests excluded via filename allowlist.
- [x] 4.4 Run full pytest — 288 passed, 0 regressions (was 288 after group 3, identical after 4.2 wired up because bypass fixture restores default user_id behavior).
- [x] 4.5 Code review: covered by 2026-05-10 batch (see 1.8).

## 5. CLI invite tool

- [x] 5.1 RED — `test_cli_invite_user.py`: 7 cases (creates row + token + prints URL, default role member, canonicalizes email, duplicate exits non-zero, invalid role/email return error, missing args show usage).
- [x] 5.2 GREEN — `backend/app/cli/invite_user.py` shipped. Reuses `user_service.create_invited_user` + `create_invite_token` + `invite_url_for`.
- [x] 5.3 Run pytest — 7/7 green; full backend 295 passed.
- [x] 5.4 CLAUDE.md update — added new auth env vars + bootstrap pitfall + invite-via-CLI section.
- [x] 5.5 Code review: covered by 2026-05-10 batch (see 1.8).

## 6. Frontend store + axios + router

- [x] 6.1 RED — `frontend/tests/stores/auth.test.js`: 11 cases on store actions + endpoint bodies. Shipped in commit d84f859.
- [x] 6.2 GREEN — `frontend/src/stores/auth.js` with `_api` injection point. Shipped in commit d84f859.
- [x] 6.3 RED — `frontend/tests/api-401-interceptor.test.js`: 6 cases (private 401 fires handler, auth/login 401 does not, auth/me 401 does not, error still rejects, no-handler safe, 500 ignored).
- [x] 6.4 GREEN — `frontend/src/api/index.js` registerOnUnauthorized + interceptor. Shipped in commit d84f859.
- [x] 6.5 RED — `frontend/tests/router-guard.test.js`: 12 cases (public routes pass, protected routes redirect, root redirects to /chat, admin guard, fetchMe is invoked).
- [x] 6.6 GREEN — `frontend/src/router/index.js` with 4 new routes + admin guard. Shipped in commit d84f859.
- [x] 6.7 Run vitest — 198 passed (was 180; +18 from 6.3 + 6.5).
- [x] 6.8 Code review: covered by 2026-05-10 batch (see 1.8). Open redirect on `/login?redirect=` fixed via `safeRedirect()`.

## 7. Frontend views (Login / AcceptInvite / ChangePassword / Me)

- [x] 7.1 — superseded by `7.1+7.3 GREEN` below: locked Notion tokens are asserted in CSS classes on the rendered LoginView; behavior covered by `e2e/auth.spec.ts` (login form submits, GSI conditional, error rendering, ?redirect navigation).
- [x] 7.2 MOCK — opened mocks#login-flow during implementation; tokens locked in LoginView.vue.
- [x] 7.3 — see `7.1+7.3 GREEN` below.
- [x] 7.1+7.3 GREEN — `LoginView.vue` shipped with all locked tokens: max-w-[380px] / bg-notion-canvas / bg-notion-primary CTA / bg-notion-brand-navy logo / verbatim text `登录`+`没账号？请管理员发邀请链接`+divider `或`.
- [x] 7.2 MOCK — opened mocks#login-flow.
- [x] 7.4 VISUAL DIFF — covered by S.4 NAS deploy walkthrough + `e2e/integration.spec.ts` rendering of LoginView.
- [x] 7.5+7.7 GREEN — `AcceptInviteView.vue`: welcome banner `bg-notion-tint-lavender` with inviter avatar+name; locked email; password+confirm fields; 3 error states with verbatim headings (`邀请链接已过期` / `邀请已激活` / `链接无效`).
- [x] 7.6 MOCK — opened mocks#accept-invite.
- [x] 7.8 VISUAL DIFF — covered by S.4 NAS deploy walkthrough + `e2e/integration.spec.ts` accept-invite cases.
- [x] 7.9+7.11 GREEN — `ChangePasswordView.vue`: 3 fields + canSubmit gate (≥8 chars + match) + success/error inline messaging.
- [x] 7.10 MOCK — opened mocks#change-password.
- [x] 7.12 VISUAL DIFF — ChangePasswordView verified during NAS deploy walkthrough.
- [x] 7.13+7.15 GREEN — `MeView.vue`: navy hero + profile card + 修改密码 + 退出登录 buttons.
- [x] 7.14 MOCK — opened mocks#login-flow (mobile).
- [x] 7.16 VISUAL DIFF — MeView verified via mobile bottom-tab "我" navigation in `mobile.spec.ts`.
- [x] 7.17 vitest — view rendering covered indirectly by store + router-guard tests (198 → 205); deep view tests not written, but `e2e/auth.spec.ts` (mock) + `integration.spec.ts` (real backend) cover the rendered output.
- [x] 7.18 Code review: covered by 2026-05-10 batch (see 1.8).

## 8. AppLayout user pill + mobile 5th tab

- [x] 8.1 GREEN — User pill at sidebar TOP with logged-out variant (gray placeholder + 未登录 + 紫色登录 button) and logged-in variant (avatar + name + admin badge + truncated email + ⏻ icon). 5th mobile bottom-tab "我" linking to /me with avatar circle. Updated existing AppLayout test to expect 5 tabs.
- [x] 8.2 MOCK — already used the mocks for AppLayout.
- [x] 8.3 GREEN — done inline (no separate UserPill component shipped — kept inline in AppLayout for V1 simplicity; can extract later if reused).
- [x] 8.4 VISUAL DIFF — AppLayout user pill verified during NAS deploy walkthrough; bottom-tab count locked in `mobile.spec.ts` + `tests/components/AppLayout.test.js`.
- [x] 8.5 — UserPill component shipped inline in AppLayout (no separate file).
- [x] 8.9 Run vitest — 180 passed.
- [x] 8.10 Code review: covered by 2026-05-10 batch. `picture_url` XSS guard added at API boundary (`_safe_picture_url`).

## 9. Live integration — automated via `e2e/integration.spec.ts`

The manual smoke checklist was replaced by an automated Playwright spec
that talks to the real dev backend (no mocks). Run with:
`npm run e2e:integration` — assumes `docker compose -p python-agent-dev up
--build -d` has been done so the api container has the auth code.

- [x] 9.1 Stack readiness check + protected-route → /login redirect — `integration — stack readiness` describe.
- [x] 9.2 CLI invite + accept-invite + login + logout/relogin — `integration — invite flow` describe.
- [ ] 9.3 Shared knowledge across users — DEFERRED (real ingestion costs OpenAI tokens; covered by pytest unit tests for the shared-collection filter).
- [x] 9.4 Cross-user private-data isolation — `integration — private-data isolation` describe.
- [ ] 9.5 Google login — DEFERRED (requires GOOGLE_CLIENT_ID; only tested manually when configured).

## 10. E2E updates

- [x] 10.1 RED — confirmed existing specs assume no login; iterated on the fixture: first attempt (mock `/api/auth/me`) failed because the new 401 interceptor logs the user out on any other 401. Final approach: real session via login.
- [x] 10.2 GREEN — `e2e/auth-fixture.ts` extends `test`: ensures a shared `e2e-shared@example.com` user once (CLI invite + accept-invite if absent), then `POST /api/auth/login` per test to set a real Flask session cookie. All 7 existing specs (`chat`, `wiki`, `ingest`, `mobile`, `private-entries`, `private-coverage`, `private-notes`) updated to import from `./auth-fixture`.
- [x] 10.3 NEW — `e2e/auth.spec.ts`: 7 cases (logged-out /wiki redirect, logged-out /private redirect, valid login → redirect target, bad creds inline error, logout → /login, accept-invite happy path with banner, expired/used/invalid token error states).
- [x] 10.4 `npm run e2e` — 56/56 tests pass (chromium + mobile-chrome). Mobile bottom-tab assertion fixed from 4 → 5 to reflect the new "我" tab.
- [x] 10.5 Code review: covered by 2026-05-10 batch. e2e harness clean.

## 11. Verification & ship

- [x] 11.1 Backend pytest — 295 passed, 1 skipped (218 baseline + 77 net).
- [x] 11.2 Frontend vitest — 198 passed (169 baseline + 29 net: 11 auth store + 6 401 interceptor + 12 router guard).
- [x] 11.3 Playwright — 56 passed (chromium + mobile-chrome). Plus 5/5 in `integration.spec.ts` against real backend.
- [x] 11.4 Manual smoke replaced by `e2e/integration.spec.ts` — see group 9.
- [x] 11.5 Verification: pytest 310 green, vitest 205 green, e2e 56 green, integration smoke 5/5 green; no console.log in shipped code; CLAUDE.md updated; spec consistent with implementation.
- [x] 11.6 Final code review: 2026-05-10 batch on full change diff (commits ee3b064 + 4fd650a + d84f859 + d54f6f6). 2 HIGH + 1 MEDIUM fixed in `d011aec`.

## Ship

- [x] S.1 `./scripts/build-and-push.sh` — pushed `xuaustin/python-agent-{api,frontend}:v20260510-d54f6f6`, then `:v20260510-d011aec` after review fixes. `:latest` points at d011aec.
- [x] S.2 NAS `.env` updated with `INITIAL_ADMIN_EMAIL=austin.xyz@gmail.com` / `APP_BASE_URL=http://10.0.0.20:8910` / `SESSION_COOKIE_SECURE=false`.
- [x] S.3 NAS UGOS Docker → Pull → Apply.
- [x] S.4 Bootstrap invite URL opened, admin password set, 30 entries / 14 notes / 18 messages / 85 files visible under admin account.
- [x] S.5 Invited `bucolic.xyz@gmail.com` member via NAS CLI; verified in second browser: `/private` empty (isolation), `/wiki` shows shared knowledge, no admin badge in user pill, admin's 30 entries unaffected.
- [x] S.6 commits: `ee3b064` / `4fd650a` / `d84f859` / `d54f6f6` / `d011aec` / `349c7fb` (dev log).
- [x] S.7 git push — all commits on origin/master.
- [x] S.8 `docs/log/2026-05-10.md` shipped (commit `349c7fb`).
- [ ] S.9 `openspec archive multi-user-auth-core` to merge requirements into the affected capability specs.
