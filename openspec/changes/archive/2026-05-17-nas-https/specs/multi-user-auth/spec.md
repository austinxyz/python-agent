## MODIFIED Requirements

### Requirement: Session cookie security via SESSION_COOKIE_SECURE env var
The system SHALL read `SESSION_COOKIE_SECURE` env var (default `true`) and set Flask's `SESSION_COOKIE_SECURE` config accordingly. After `nas-https` lands, NAS deploys use the default `true` (HTTPS-only cookies). Local dev on `localhost` may set `SESSION_COOKIE_SECURE=false` since browsers treat `localhost` as a "secure context" for many purposes but still require the `Secure` attribute to be absent for plain HTTP. `SameSite=Lax` and `HttpOnly=True` are always set regardless of `Secure`.

#### Scenario: Cookie has Secure attribute when env var unset
- **WHEN** `SESSION_COOKIE_SECURE` env var is unset and a login response is sent
- **THEN** the `Set-Cookie` header includes `Secure`, `HttpOnly`, and `SameSite=Lax` attributes

#### Scenario: Cookie omits Secure when env var is "false"
- **WHEN** `SESSION_COOKIE_SECURE=false` and a login response is sent
- **THEN** the `Set-Cookie` header includes `HttpOnly` and `SameSite=Lax` but NOT `Secure`

#### Scenario: NAS deploy uses Secure cookie after nas-https lands
- **WHEN** the NAS `.env` no longer sets `SESSION_COOKIE_SECURE` (the line is removed) and a login response is sent over HTTPS
- **THEN** the `Set-Cookie` header includes `Secure` and the cookie is rejected by browsers if the request was over plain HTTP (which the tailnet entry no longer permits)

## ADDED Requirements

### Requirement: Admin role gates admin-only API endpoints
The system SHALL provide a `@require_admin` decorator (or equivalent) that combines `@require_auth` with an additional `g.user.role === 'admin'` check. Routes under `/api/admin/*` SHALL use this decorator. Non-admin authenticated users receive HTTP 403 `{"error": "admin required"}`. Unauthenticated requests receive HTTP 401 via the underlying `@require_auth`.

#### Scenario: Admin-only endpoint accepts admin
- **WHEN** an admin-authenticated request hits any `/api/admin/*` endpoint that uses `@require_admin`
- **THEN** the request proceeds to the handler and returns HTTP 200 (or whatever the handler specifies)

#### Scenario: Admin-only endpoint rejects member
- **WHEN** a member-authenticated request hits any `/api/admin/*` endpoint
- **THEN** the response is HTTP 403 with body `{"error": "admin required"}` and the handler is NOT invoked

#### Scenario: Admin-only endpoint rejects unauthenticated
- **WHEN** an unauthenticated request hits any `/api/admin/*` endpoint
- **THEN** the response is HTTP 401 (standard `@require_auth` behavior) and the admin-check is NOT reached
