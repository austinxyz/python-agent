## ADDED Requirements

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
