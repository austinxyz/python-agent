## Purpose

Defines the Vue 3 + Vite frontend scaffold and shared chrome: project bootstrap, routing, axios setup, top-level AppLayout (with mobile bottom-tab variant), shared TreeNav, and PWA manifest. Per-view capabilities (chat-view, ingest-view, etc.) extend this.
## Requirements
### Requirement: Vue 3 + Vite project with Pinia and Vue Router
The system SHALL have a `frontend/` directory initialised as a Vue 3 + Vite project with the following dependencies: `vue`, `vue-router`, `pinia`, `axios`. Dev dependencies: `vite`, `@vitejs/plugin-vue`, `vitest`, `@vue/test-utils`, `happy-dom`. The project MUST include a `vite.config.js` that configures the Vue plugin and a dev-server proxy: `server.proxy['/api'] = 'http://localhost:5000'`.

#### Scenario: Frontend dev server starts
- **WHEN** `cd frontend && npm run dev` is run
- **THEN** Vite starts without errors and the app is accessible at `http://localhost:3000`

#### Scenario: API calls are proxied
- **WHEN** the frontend makes an `axios.get('/api/health')` call during development
- **THEN** the request is forwarded to `http://localhost:5000/api/health` without CORS errors

### Requirement: Axios instance configured with /api baseURL
The system SHALL provide `frontend/src/api/index.js` that creates and exports a single Axios instance with `baseURL: '/api'`. All API calls in stores and components MUST import from this module. API calls MUST NOT prepend `/api` again (e.g., use `api.get('/wiki')`, not `api.get('/api/wiki')`).

#### Scenario: Axios baseURL is /api
- **WHEN** `import api from '@/api'` is used and `api.get('/wiki')` is called
- **THEN** the HTTP request goes to `/api/wiki`

### Requirement: App layout shell with left navigation
The system SHALL provide `frontend/src/App.vue` that renders `AppLayout.vue`. `AppLayout.vue` MUST implement a fixed left navigation bar of width 100px containing four navigation items with icons and labels: 📚 知识库 (links to `/wiki`), ⬆ 摄入 (links to `/ingest`), 💬 对话 (links to `/chat`), 🔒 私有 (links to `/private`). The active nav item MUST be highlighted using Vue Router's `router-link-active` class. The right side of the layout MUST contain a `<router-view />` slot for the current page.

#### Scenario: Left nav renders all four items
- **WHEN** the app is loaded at any route
- **THEN** all four navigation items are visible in the left sidebar

#### Scenario: Active nav item is highlighted
- **WHEN** the user navigates to `/chat`
- **THEN** the 💬 对话 nav item has the `router-link-active` class applied

### Requirement: Four view skeletons with Vue Router routes
The system SHALL provide four view components under `frontend/src/views/`: `WikiView.vue`, `IngestView.vue`, `ChatView.vue`, `PrivateView.vue`. Each view MUST render a heading with the page name (e.g., `<h1>知识库</h1>`). Vue Router MUST map: `/wiki` → `WikiView`, `/ingest` → `IngestView`, `/chat` → `ChatView`, `/private` → `PrivateView`. The root path `/` MUST redirect to `/wiki`.

#### Scenario: Navigation routes to correct view
- **WHEN** the user navigates to `/ingest`
- **THEN** `IngestView.vue` is rendered in the `<router-view />`

#### Scenario: Root redirect
- **WHEN** the user navigates to `/`
- **THEN** the router redirects to `/wiki` and `WikiView.vue` is rendered

### Requirement: TreeNav.vue stub component
The system SHALL provide `frontend/src/components/tree-nav/TreeNav.vue` that accepts two props: `items` (array of tree nodes) and `onSelect` (function called with the selected node). For this change, the component MUST render a `<ul>` list of the top-level item labels. The full tree expand/collapse behaviour is deferred to a feature change. The component MUST NOT duplicate tree logic — it is the single source of truth for tree navigation across the wiki page and the ingest files tab.

#### Scenario: TreeNav renders item labels
- **WHEN** `<TreeNav :items="[{label:'Finance'},{label:'Health'}]" :onSelect="() => {}" />` is rendered
- **THEN** the component displays "Finance" and "Health" as list items

### Requirement: Four Pinia store stubs
The system SHALL provide four Pinia store files under `frontend/src/stores/`: `wiki.js`, `ingest.js`, `chat.js`, `private.js`. Each store MUST export a `use<Domain>Store` composable (e.g., `useWikiStore`) and define at minimum an empty `state` object. Stores are empty stubs; feature changes populate them with state, getters, and actions.

#### Scenario: Stores are importable without error
- **WHEN** any of the four store composables are imported in a component
- **THEN** no import or runtime error occurs and the store is accessible via `useWikiStore()` etc.

### Requirement: Frontend vitest smoke test
The system SHALL include a `frontend/tests/` directory with `smoke.test.js` that: mounts `AppLayout.vue` and asserts the four nav items are present; mounts each of the four view components and asserts their heading is present. Tests MUST use `@vue/test-utils` with `happy-dom` as the test environment.

#### Scenario: Frontend smoke tests pass
- **WHEN** `cd frontend && npm test` is run
- **THEN** all smoke tests pass with exit code 0

### Requirement: AppLayout uses bottom tab bar below md, sidebar at md+
`frontend/src/components/AppLayout.vue` SHALL render two distinct layouts based on viewport width using Tailwind's `md:` (768px) breakpoint. Below `md`: a 56px-tall bottom tab bar fixed at `bottom: 0` with `padding-bottom: env(safe-area-inset-bottom)`, listing the same 4 nav items as the desktop sidebar. At `md` and above: the existing left sidebar (collapsible w-56/w-16). Both variants SHALL share the same `navItems` array and `useRoute` active-state logic.

#### Scenario: Phone viewport renders bottom tab bar
- **WHEN** the viewport is 393px wide
- **THEN** `<aside>` (sidebar) is hidden, a bottom-fixed `<nav>` element with role `navigation` renders 4 tab items, and `safe-area-inset-bottom` is applied as bottom padding

#### Scenario: Desktop viewport renders left sidebar
- **WHEN** the viewport is 1280px wide
- **THEN** the left sidebar renders as today (w-56 expanded / w-16 collapsed); no bottom tab bar is rendered

#### Scenario: Active nav item styling is consistent across variants
- **WHEN** the user is on `/chat` at any viewport
- **THEN** the corresponding tab/sidebar item is visually marked active using `bg-notion-tint-lavender text-notion-brand-purple-800` (Notion design tokens)

### Requirement: AppLayout removes blue→purple gradient in favor of Notion design tokens
The legacy `bg-gradient-to-r from-blue-500 to-purple-600` logo background and `bg-primary/10 text-primary` active-state classes in `AppLayout.vue` SHALL be replaced by Notion design system tokens. The logo SHALL render as a navy monochrome mark (no gradient). The active-state styling SHALL match the rest of the redesigned views (per `docs/design/notion.md`). No other view component SHALL import the now-orphaned `primary` Tailwind utility for this purpose.

#### Scenario: No leftover gradient classes in AppLayout
- **WHEN** the `AppLayout.vue` source is grepped for `from-blue` or `to-purple`
- **THEN** no matches are found

### Requirement: Project includes PWA manifest and apple-touch-icon
The repository SHALL include `frontend/public/manifest.json` declaring `name`, `short_name`, `start_url`, `display: "standalone"`, `theme_color` matching Notion design system primary, `background_color`, and at minimum three icon entries (192px, 512px, and 512px maskable). `frontend/index.html` SHALL include `<link rel="manifest" href="/manifest.json">`, `<link rel="apple-touch-icon" href="/icons/192.png">`, and `<meta name="theme-color" content="...">` matching the manifest. The icons themselves SHALL exist at `frontend/public/icons/`.

#### Scenario: Manifest is served by the frontend container
- **WHEN** a browser fetches `http://10.0.0.20:8910/manifest.json`
- **THEN** the response is HTTP 200 with content-type `application/manifest+json` and parses as valid JSON containing the above fields

#### Scenario: Add to home screen launches in standalone mode
- **WHEN** the user adds the app to home screen on iOS Safari and launches from the home screen icon
- **THEN** the app opens without browser chrome (URL bar hidden, full-viewport app)

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
`frontend/src/views/LoginView.vue` SHALL render a centered card (`max-w-[380px]` on desktop) inside the standard AppLayout main pane (sidebar visible). The card uses `bg-notion-canvas` background with `border-notion-hairline` border. The CTA button uses `bg-notion-primary text-notion-on-primary`. The Google button uses `bg-notion-canvas border-notion-hairline-strong`.

Card contents (in this order): logo block (navy `bg-notion-brand-navy` 知 mark), heading `登录` (text `text-notion-ink`), subtitle `使用邮箱密码 或 Google 账号`, email input, password input, "登录" CTA button, divider with literal text `或`, "Sign in with Google" button rendered ONLY when `auth.config.has_google === true` AND (`window.location.protocol === 'https:'` OR `hostname` matches `^(localhost|127\.0\.0\.1)$`), and a final hint text `没账号？请管理员发邀请链接` styled `text-notion-stone`.

Error messages render inline above the form using `text-notion-error` color. After successful login, push to `?redirect` if present, else `/chat`.

#### Scenario: GSI button rendered on https origin
- **WHEN** the page loads on `https://example.com/login` and `config.has_google` is true
- **THEN** `data-google-signin` button is visible

#### Scenario: GSI button hidden on http://10.0.0.20
- **WHEN** the page loads on `http://10.0.0.20:8910/login` (non-localhost, non-HTTPS) and `config.has_google` is true
- **THEN** `data-google-signin` button is NOT in the DOM

#### Scenario: Successful login redirects honoring ?redirect=
- **WHEN** user submits valid credentials with URL `/login?redirect=/private`
- **THEN** after the action resolves, the router is at `/private`

#### Scenario: Locked tokens + text strings present
- **WHEN** LoginView renders
- **THEN** the card root has classes matching `/max-w-\[380px\]/` AND `/bg-notion-canvas/`; the CTA button classes match `/bg-notion-primary/`; the visible text contains both `登录` and `没账号？请管理员发邀请链接`

### Requirement: AcceptInviteView at /accept-invite
`frontend/src/views/AcceptInviteView.vue` SHALL read `token` query param, call `GET /api/auth/invite/<token>` on mount, and render one of: (a) a welcome banner ("<inviter> 邀请你加入") + locked email field + new-password + confirm-password fields + "完成注册并登录" CTA, (b) error states for expired / used / invalid tokens. On submission with matching passwords (both ≥ 8 chars), POST to `/api/auth/accept-invite`. Success → push to `/chat`.

The welcome banner uses `bg-notion-tint-lavender` background. The CTA uses `bg-notion-primary text-notion-on-primary`. Error states use icons + `text-notion-warning` (expired), `text-notion-brand-green` (used), `text-notion-error` (invalid). Heading text is `设置你的密码`; help text is `至少 8 个字符。设好后用邮箱+密码登录。`. The 3 error UI strings are `邀请链接已过期` / `邀请已激活` / `链接无效` (verbatim).

#### Scenario: Valid token shows welcome + form
- **WHEN** AcceptInviteView mounts with a valid unused unexpired token
- **THEN** the inviter's name + email + a password form are visible

#### Scenario: Mismatched passwords block submit
- **WHEN** new-password and confirm-password differ
- **THEN** submit button is disabled and an inline message shows

#### Scenario: Expired token renders error
- **WHEN** the GET /api/auth/invite/<token> response has `expired: true`
- **THEN** an "邀请已过期" message renders with text directing user to admin

#### Scenario: Locked tokens + text strings on welcome banner
- **WHEN** AcceptInviteView mounts with valid token
- **THEN** welcome banner element has classes matching `/bg-notion-tint-lavender/`; visible text contains `设置你的密码` and `完成注册并登录`

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

User pill background uses `bg-notion-canvas` with `border-notion-hairline`. The 登录 button uses `bg-notion-primary text-notion-on-primary`. The admin role badge uses `bg-notion-tint-lavender text-notion-brand-purple-800`. The logout icon button uses `text-notion-steel hover:text-notion-error`. Verbatim text: logged-out label `未登录`; CTA text `登录`; logout icon button title `退出`.

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

#### Scenario: User pill tokens + text locked
- **WHEN** AppLayout renders with `auth.currentUser=null`
- **THEN** the pill has `data-user-pill` attribute, classes match `/bg-notion-canvas/`, the 登录 button has classes matching `/bg-notion-primary/`, visible text contains `未登录` and `登录`

#### Scenario: Admin role badge uses lavender tokens
- **WHEN** AppLayout renders with `auth.currentUser.role='admin'`
- **THEN** the admin badge element classes match `/bg-notion-tint-lavender/` AND `/text-notion-brand-purple-800/`; visible text contains `admin`

### Requirement: Default landing changed from /wiki to /chat
The router's root redirect (`{ path: '/', redirect: ... }`) and the post-login redirect SHALL both target `/chat` instead of `/wiki` (the previous default). Per-feature views are unchanged.

#### Scenario: Authenticated user navigating to / lands on /chat
- **WHEN** an authenticated user opens `/`
- **THEN** the router lands them on `/chat`

### Requirement: Router registers /admin/cert route with admin guard
The router SHALL register `/admin/cert` with `meta: { requiresAuth: true, requiresAdmin: true }`. The global `beforeEach` guard SHALL redirect non-admin users away from `/admin/*` to `/chat` (the multi-user-auth-core router already implements this admin guard for the future `/admin/users` route; this change adds another route that inherits the same guard).

#### Scenario: Admin reaches /admin/cert
- **WHEN** an admin user navigates to `/admin/cert`
- **THEN** `AdminCertView.vue` mounts and the cert status card renders

#### Scenario: Member is redirected from /admin/cert
- **WHEN** a member user navigates to `/admin/cert`
- **THEN** the router pushes `/chat` and AdminCertView does NOT mount

#### Scenario: Logged-out user redirected to login
- **WHEN** an unauthenticated visit lands on `/admin/cert`
- **THEN** the router pushes `/login?redirect=/admin/cert` (standard requiresAuth behavior)

### Requirement: AdminCertView displays cert + Tailscale status
`AdminCertView.vue` SHALL fetch `GET /api/admin/cert-status` on mount and render the response in a card matching `docs/superpowers/specs/mocks/2026-05-10-nas-https-mocks.html`. The card has four labeled rows (Tailnet 主机名 / 证书到期 / Tailscale 连接 / 上次 renew) and a status pill in the header. Polling refreshes the data every 60 seconds.

Locked design tokens (asserted via `wrapper.classes()` in vitest):
- Card container: `bg-notion-canvas`, `border-notion-hairline`, `rounded-lg`
- "健康" pill: `bg-notion-tint-mint`, `text-notion-brand-green`
- "即将到期" pill: `bg-notion-tint-yellow`, `text-notion-warning`
- "异常" / "紧急" pill: `bg-notion-tint-rose`, `text-notion-error`
- Row label: `text-notion-steel`
- Row value: `text-notion-charcoal`, `font-mono`

Locked verbatim text strings (asserted via `wrapper.text()` in vitest):
- Page card title: `证书与 Tailscale 状态`
- Row labels: `Tailnet 主机名`, `证书到期`, `Tailscale 连接`, `上次 renew`
- Status pills: `健康`, `即将到期`, `异常`
- Days-remaining badge format: `还剩 N 天`

#### Scenario: Healthy state renders green tokens
- **WHEN** the API returns `tailscale_status: "online"` AND `days_remaining > 30`
- **THEN** the header pill has class `bg-notion-tint-mint` and text `健康`
- **AND** the days-remaining badge has class `bg-notion-tint-mint`

#### Scenario: Warning state renders yellow tokens
- **WHEN** the API returns `tailscale_status: "online"` AND `7 <= days_remaining <= 30`
- **THEN** the header pill has class `bg-notion-tint-yellow` and text `即将到期`
- **AND** the days-remaining badge has class `bg-notion-tint-yellow`

#### Scenario: Error state when Tailscale offline
- **WHEN** the API returns `tailscale_status: "offline"`
- **THEN** the header pill has class `bg-notion-tint-rose` and text `异常`
- **AND** the row values are dashes or "无法读取" (verbatim)

#### Scenario: Member sees no /admin/cert nav item
- **WHEN** `auth.currentUser.role !== 'admin'`
- **THEN** the AppLayout sidebar (desktop) does NOT render the "证书与 Tailscale 状态" link
- **AND** the MeView (mobile) does NOT render the link

### Requirement: AppLayout admin nav slot
The AppLayout sidebar (desktop, md+) SHALL conditionally render a "证书与 Tailscale 状态" nav item linking to `/admin/cert`, visible ONLY when `auth.currentUser?.role === 'admin'`. The MeView (mobile, below md) SHALL conditionally render a matching link in its admin section. This admin slot is extensible — future admin routes (e.g., `/admin/users` from the deferred `multi-user-auth-admin-ui` change) MAY add additional items into the same slot, but `nas-https` adds only the cert link.

#### Scenario: Admin sees the cert nav link in sidebar
- **WHEN** the AppLayout mounts with `auth.currentUser.role === 'admin'`
- **THEN** the sidebar includes a `router-link` with `to="/admin/cert"` and text `证书与 Tailscale 状态`

#### Scenario: Member does not see the cert nav link
- **WHEN** the AppLayout mounts with `auth.currentUser.role === 'member'`
- **THEN** the sidebar does NOT contain a `router-link` with `to="/admin/cert"`

