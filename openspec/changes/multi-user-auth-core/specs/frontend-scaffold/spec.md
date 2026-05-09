## ADDED Requirements

### Requirement: useAuthStore Pinia store
The system SHALL provide `frontend/src/stores/auth.js` exporting a Pinia store with state `{ currentUser, config, loading, error }` and actions `fetchMe`, `fetchConfig`, `loginWithPassword(email, password)`, `loginWithGoogle(idToken)`, `acceptInvite(token, password)`, `changePassword(oldPw, newPw)`, `logout()`. `currentUser` is `null` when unauthenticated; otherwise `{id, email, name, picture_url, role}`. `config` mirrors `GET /api/auth/config` (`has_google` + `google_client_id`).

#### Scenario: fetchMe populates currentUser on success
- **WHEN** `auth.fetchMe()` resolves successfully against `/api/auth/me`
- **THEN** `auth.currentUser` is the user object

#### Scenario: fetchMe sets currentUser to null on 401
- **WHEN** `auth.fetchMe()` receives 401
- **THEN** `auth.currentUser` is `null` and the error is not propagated to UI (silent — caller checks state)

### Requirement: Axios 401 response interceptor
The Axios instance at `frontend/src/api/index.js` SHALL register a response interceptor that, on any 401 response, calls `auth.currentUser = null` and pushes the router to `/login` with `?redirect=<originalPath>`. Endpoints under `/api/auth/*` are exempt (login itself returning 401 must not trigger the interceptor). The interceptor SHALL preserve the original error so callers can still see status / body.

#### Scenario: 401 from /api/private redirects to login
- **WHEN** `auth.fetchMe()` returned a valid user, then `GET /api/private/entries` returns 401 (e.g., admin disabled the user)
- **THEN** `auth.currentUser` becomes null and the router is at `/login?redirect=/private`

#### Scenario: 401 from /api/auth/login does not trigger redirect
- **WHEN** `auth.loginWithPassword('x', 'y')` returns 401
- **THEN** the redirect is NOT triggered; the LoginView shows an inline error from the action's rejection

### Requirement: Router auth guard
`frontend/src/router/index.js` SHALL register a global `beforeEach` guard that:
- Allows public routes `/login` and `/accept-invite?token=...` without auth.
- For all other routes: if `auth.currentUser` is null, calls `auth.fetchMe()` (one-shot to populate from cookie if present); if still null, redirects to `/login?redirect=<targetPath>`.
- After successful `fetchMe`, applies admin-only restrictions for paths starting with `/admin/` (currently no such routes ship in this change; the rule is in place for `multi-user-auth-admin-ui`).
- Preserves `?redirect=` on `/login` redirects so post-login goes back to the intended page.

The router SHALL also set the root path `/` to redirect to `/chat` (changed from `/wiki`).

#### Scenario: Unauthenticated user accessing /private gets redirected to /login
- **WHEN** the router navigates to `/private` and `auth.currentUser` is null AND `fetchMe()` returns null
- **THEN** the route resolves to `/login?redirect=/private`

#### Scenario: Authenticated user navigating to / lands on /chat
- **WHEN** an authenticated user navigates to `/`
- **THEN** the router redirects to `/chat`

#### Scenario: Public routes don't trigger auth check
- **WHEN** an unauthenticated user navigates to `/login` or `/accept-invite?token=abc`
- **THEN** no `fetchMe` call is made and no redirect occurs

### Requirement: LoginView at /login
`frontend/src/views/LoginView.vue` SHALL render a centered card (max-width 380px on desktop) inside the standard AppLayout main pane (sidebar visible). Card contains: email input, password input, "登录" CTA button, divider "或", "Sign in with Google" button (rendered ONLY when `auth.config.has_google === true` AND (`window.location.protocol === 'https:'` OR hostname matches `^(localhost|127\.0\.0\.1)$`)). Error messages render inline above the form. After successful login, push to `?redirect` if present, else `/chat`.

#### Scenario: GSI button rendered on https origin
- **WHEN** the page loads on `https://example.com/login` and `config.has_google` is true
- **THEN** `data-google-signin` button is visible

#### Scenario: GSI button hidden on http://10.0.0.20
- **WHEN** the page loads on `http://10.0.0.20:8910/login` (non-localhost, non-HTTPS) and `config.has_google` is true
- **THEN** `data-google-signin` button is NOT in the DOM

#### Scenario: Successful login redirects honoring ?redirect=
- **WHEN** user submits valid credentials with URL `/login?redirect=/private`
- **THEN** after the action resolves, the router is at `/private`

### Requirement: AcceptInviteView at /accept-invite
`frontend/src/views/AcceptInviteView.vue` SHALL read `token` query param, call `GET /api/auth/invite/<token>` on mount, and render one of: (a) a welcome banner ("<inviter> 邀请你") + locked email field + new-password + confirm-password fields + "完成注册并登录" CTA, (b) error states for expired / used / invalid tokens. On submission with matching passwords (both ≥ 8 chars), POST to `/api/auth/accept-invite`. Success → push to `/chat`.

#### Scenario: Valid token shows welcome + form
- **WHEN** AcceptInviteView mounts with a valid unused unexpired token
- **THEN** the inviter's name + email + a password form are visible

#### Scenario: Mismatched passwords block submit
- **WHEN** new-password and confirm-password differ
- **THEN** submit button is disabled and an inline message shows

#### Scenario: Expired token renders error
- **WHEN** the GET /api/auth/invite/<token> response has `expired: true`
- **THEN** an "邀请已过期" message renders with text directing user to admin

### Requirement: ChangePasswordView at /change-password
`frontend/src/views/ChangePasswordView.vue` SHALL render an authenticated-only form with old / new / confirm fields. Submit POSTs to `/api/auth/change-password`. Success shows a brief success state then navigates to `/me` (mobile) or stays on the page with a confirmation message (desktop). Error messages render inline.

#### Scenario: Successful password change shows confirmation
- **WHEN** user submits correct old + valid new + matching confirm
- **THEN** the API returns 200 and the UI shows "✓ 密码已更新"

#### Scenario: Wrong old password shows inline error
- **WHEN** API returns 401 `{error: "old password incorrect"}`
- **THEN** the form shows the error inline; new + confirm fields preserve their values

### Requirement: MeView at /me (mobile-only profile menu)
`frontend/src/views/MeView.vue` SHALL render the user's profile + actions as a full-page mobile menu. Contents: avatar + name + email + role badge card; "修改密码" link to `/change-password` (only if `password_hash` is set, i.e., user has password auth); "退出登录" button. The view is reachable via the bottom-tab "我" (5th tab) on mobile. Desktop AppLayout exposes the same actions via a popover anchored on the user pill (no separate route).

#### Scenario: MeView mounts with current user info
- **WHEN** authenticated user navigates to /me
- **THEN** their email + name + role badge are visible

#### Scenario: Logout returns to /login
- **WHEN** user taps "退出登录" on MeView
- **THEN** auth.logout is called, currentUser becomes null, and router is at /login

### Requirement: AppLayout user pill (sidebar top + mobile 5th tab)
`AppLayout.vue` SHALL add a user pill at the **top** of the desktop sidebar (above the existing logo and nav). Logged-out state: gray placeholder avatar + "未登录" label + 紫色【登录】button (router-link to /login). Logged-in state: avatar (Google `picture_url` if present, else first letter of email on a hash-derived background color) + name + role badge ("admin" lavender background for admins; member has no badge) + email truncated + ⏻ logout icon button. Clicking the pill (logged-in only) opens an upward-flyout menu with 修改密码 / 退出登录 entries.

The mobile bottom-tab nav SHALL gain a **5th tab "我"** linking to `/me`. The active state of "我" mirrors the existing tab styling (`bg-notion-tint-lavender text-notion-brand-purple-800`). Total mobile tabs: 知识库 / 摄入 / 对话 / 私有数据 / 我.

#### Scenario: Logged-out sidebar shows login button
- **WHEN** AppLayout renders with `auth.currentUser = null`
- **THEN** the user pill at top of sidebar shows "未登录" + a clickable "登录" button

#### Scenario: Logged-in sidebar shows avatar + email
- **WHEN** AppLayout renders with `auth.currentUser = {email: 'a@b.com', role: 'admin', ...}`
- **THEN** the user pill shows the avatar, "admin" badge, "a@b.com" truncated, and a logout icon

#### Scenario: Mobile bottom-tab has 5 items including "我"
- **WHEN** AppLayout renders at viewport 393px and `auth.currentUser` is set
- **THEN** `[data-bottom-tabs]` contains 5 router-link children, the last one labeled "我" linking to /me

#### Scenario: Mobile when logged out: bottom-tab still 5 items but tap → /login redirect
- **WHEN** AppLayout renders at mobile viewport with `auth.currentUser=null` AND user is on /login (so tab is visible)
- **THEN** clicking any tab triggers the router auth guard → redirects to /login (no error)

### Requirement: Default landing changed from /wiki to /chat
The router's root redirect (`{ path: '/', redirect: ... }`) and the post-login redirect SHALL both target `/chat` instead of `/wiki` (the previous default). Per-feature views are unchanged.

#### Scenario: Authenticated user navigating to / lands on /chat
- **WHEN** an authenticated user opens `/`
- **THEN** the router lands them on `/chat`
