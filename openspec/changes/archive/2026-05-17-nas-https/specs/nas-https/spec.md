## ADDED Requirements

### Requirement: TLS termination via Tailscale serve on port 443
The system SHALL terminate TLS on the NAS host using `tailscale serve --https=443 http://localhost:8910`. The Tailscale daemon is installed via UGOS App Center (not as a Docker container in `docker-compose.prod.yml`). The serve config persists across host reboots in `/var/lib/tailscale`. There SHALL be no additional reverse-proxy container (no Caddy, no Traefik) — Tailscale serve fulfills the TLS-termination + reverse-proxy role.

#### Scenario: TLS terminator runs on host network
- **WHEN** the NAS boots and Tailscale daemon starts
- **THEN** `tailscale serve status` reports an active mapping from `https://python-agent.<tailnet-id>.ts.net:443` to `http://localhost:8910`

#### Scenario: TLS terminator survives Docker compose restart
- **WHEN** `docker compose -f docker-compose.prod.yml restart` is run
- **THEN** Tailscale serve config remains intact (it lives outside Docker on the host) and the HTTPS endpoint continues to respond

### Requirement: Cert provisioning via Tailscale-issued Let's Encrypt
The system SHALL use the cert that Tailscale provisions through its DNS-01 ACME challenge for the tailnet-hosted hostname `python-agent.<tailnet-id>.ts.net`. The cert is publicly trusted (Let's Encrypt root CA in every modern browser). Tailscale daemon auto-renews; no in-app renewal logic. The cert files live on the NAS host at `/var/lib/tailscale/certs/`.

#### Scenario: Browser shows a green lock without warning
- **WHEN** a Tailscale-connected device opens `https://python-agent.<tailnet-id>.ts.net/`
- **THEN** the browser displays the page with a valid TLS indicator (Let's Encrypt cert chain) and no `--insecure` flag or click-through warning is needed

#### Scenario: GSI library loads on the HTTPS origin
- **WHEN** the LoginView renders on the tailnet HTTPS URL
- **AND** `config.has_google === true` (because `GOOGLE_CLIENT_ID` env var is set)
- **THEN** the GSI button is visible and clicking it successfully completes Google Sign-In

### Requirement: GET /api/admin/cert-status (admin-only)
The system SHALL expose `GET /api/admin/cert-status` returning JSON `{hostname, cert_expiry_iso, days_remaining, tailscale_status, last_renew_iso}`. The endpoint requires `@require_auth` AND `g.user.role === 'admin'`. Member users receive HTTP 403. The endpoint reads from `tailscale status --json` (subprocess) and from the cert file metadata on disk.

#### Scenario: Admin reads cert status
- **WHEN** an admin-authenticated user calls `GET /api/admin/cert-status`
- **THEN** the response is HTTP 200 with the five fields populated from Tailscale CLI output and cert file metadata

#### Scenario: Member is rejected
- **WHEN** a member-authenticated user calls `GET /api/admin/cert-status`
- **THEN** the response is HTTP 403 with body `{"error": "admin required"}`

#### Scenario: Unauthenticated request is rejected
- **WHEN** a request with no session cookie calls `GET /api/admin/cert-status`
- **THEN** the response is HTTP 401 (standard `@require_auth` behavior)

#### Scenario: Tailscale daemon offline
- **WHEN** the Tailscale CLI fails (daemon not running, returns non-zero exit)
- **THEN** the endpoint returns HTTP 200 with `tailscale_status: "offline"` and `hostname: null`, `cert_expiry_iso: null`, `days_remaining: null`, `last_renew_iso: null` (does not error out — admin UI displays the error state)

### Requirement: Plain HTTP LAN entry removed
The system SHALL remove the `8910:3000` port mapping from `docker-compose.prod.yml` on NAS deploys. The frontend container still listens on port 80 internally, accessible to the Tailscale serve daemon via `localhost:8910` (the previous host port binding). No LAN-direct HTTP entry point remains. Emergency recovery is via NAS host shell (UGOS terminal), not via plain HTTP.

#### Scenario: Old URL no longer responds
- **WHEN** a curl request goes to `http://10.0.0.20:8910/`
- **THEN** the connection is refused (port not bound on host) — no fallback HTTP server is configured

### Requirement: APP_BASE_URL points at the tailnet hostname
The system SHALL set `APP_BASE_URL=https://python-agent.<tailnet-id>.ts.net` in NAS `.env`. Invite URLs printed by the CLI (`docker exec ... python -m app.cli.invite_user`) embed this base URL. Family members opening the invite URL land at the tailnet HTTPS hostname.

#### Scenario: CLI prints tailnet invite URL
- **WHEN** admin runs `docker exec python-agent-api python -m app.cli.invite_user foo@example.com member`
- **THEN** stdout includes `Invite URL: https://python-agent.<tailnet-id>.ts.net/accept-invite?token=...`
