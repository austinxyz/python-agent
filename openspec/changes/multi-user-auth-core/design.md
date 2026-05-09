## Context

Full requirements + UI mocks are in source-of-truth files referenced from the proposal. This design captures the **decisions** with their alternatives, so that future readers (including future-me) understand why each choice was made — not just what was made.

Current state: `user_id="default"` is hardcoded in 5 route files (`files.py`, `ingest.py`, `chat.py`, `private.py`, `wiki.py`). All 5 SQLite tables (`files`, `chat_sessions`, `notes`, `private_entries`, `chat_messages`) carry a `user_id` column that's unused for filtering today. Qdrant `private` collection enforces a `user_id` payload filter on every search call already. Schema is multi-user-ready; only the bridge from "request → identity" is missing.

V1 scale: ~5 users, single instance, NAS-first deploy. Decisions favor simplicity over horizontal scalability.

## Goals / Non-Goals

**Goals:**
- Replace hardcoded `user_id="default"` with real per-request identity.
- Email+password login works on NAS HTTP (no HTTPS dependency).
- Google Sign-In works as additional method on HTTPS / localhost without breaking when missing.
- Bootstrap migration is automatic, idempotent, and never loses existing data.
- Disabled users can't continue using the app after the admin disables them (bounded by latency of `users.status` per-request check).
- All 5 existing route files get `@require_auth` + `g.user.id` substitution with no behavior regression.

**Non-Goals:**
- Rate limiting (separate hardening change).
- Session revocation (V1 = "disable kills next request"; stronger model in hardening change).
- Admin UI (separate `multi-user-auth-admin-ui` change).
- HTTPS / cloud (separate changes).
- Households / shared private data (separate change).
- Self-service password reset via email (admin disable + reinvite is V1 recovery).

## Decisions

### 1. One coherent change for backend + frontend (no further splitting in core)

**Choice:** Backend auth, all frontend auth views (login / accept-invite / change-password / me), AppLayout user pill, router guard, and bootstrap migration ship together as `multi-user-auth-core`.

**Alternatives considered:**
- *Backend-first, frontend-second:* would leave a backend that nobody can use without curl. Worse than current state.
- *Token-only frontend (no UI for change-password / me):* incomplete; admin can't even change their own password without an endpoint, but a UI-less endpoint is hostile.

**Why one change:** auth is intrinsically end-to-end. Splitting backend/frontend creates a "half deployed" state that's worse than the current single-user mode.

### 2. Single `users` table representing both allowlist AND active users (state machine)

**Choice:** One table; `status` column flips through `invited` → `active` → `disabled`. Email is the canonical identity (lowercased + trimmed).

**Alternatives considered:**
- *Separate `allowed_emails` + `users` tables:* cleaner conceptually but doubles the joins + admin UI complexity. The "invited but not yet seen" row is naturally the same logical entity as the "active user" — splitting is artificial.
- *No allowlist, just check Google domain:* doesn't work for email+password (no domain to check) and exposes the instance to anyone with a Google account.

**Why state machine:** matches Mastodon, GitHub Org, GitLab patterns. One table, easy queries, status is the source of truth for "can this person log in now?".

### 3. Password (argon2id) AND Google login coexist on the same user row

**Choice:** Each user row can have `password_hash`, `google_sub`, both, or neither (during invited state). On Google login, if email matches an `active` row with no `google_sub` yet, link automatically. If `google_sub` mismatch → 403.

**Alternatives considered:**
- *One auth method per user (admin chooses at invite time):* simpler, but inflexible — user can't fall back to password if they lose Google access.
- *Google-only:* requires HTTPS; breaks NAS HTTP deployment. The whole point of the dual scheme is HTTP fallback.
- *Magic link via email:* requires SMTP infra; deferred.

**Why both:** every user is guaranteed a password fallback (NAS HTTP can always work), and Google is a no-friction option when HTTPS is available. The auto-linking on first Google login is the "user signed up via password but later wants Google" path.

### 4. Email canonicalization at every read & write (`.strip().lower()`)

**Choice:** Lowercase + trim every email at every boundary — bootstrap insert, admin invite, JWT email claim lookup, login form, accept-invite. Tests assert `Austin@Gmail.com` resolves to the same row as `austin@gmail.com`.

**Alternatives considered:**
- *Store as-typed, normalize only on lookup:* leads to two rows for the same person if someone types differently in different invites.
- *DB-level case-insensitive collation:* SQLite supports `COLLATE NOCASE` but it's a magic flag; explicit Python normalization is more visible and testable.

**Why explicit:** prevents data integrity bugs that are nearly impossible to debug. Cheap.

### 5. Disabled-user enforcement via per-request `status` check (not session_version)

**Choice:** `@require_auth` middleware loads `users.status` on every request; if not `'active'`, clear cookie + 401. No `session_version` column.

**Alternatives considered:**
- *session_version column + cookie carries version:* full revocation on disable. Considered for v2 of requirements doc; dropped in slim because for V1 family scale, disabled-then-still-using-cached-session is unlikely (you'd have to disable a user who's mid-session). Per-request status check + 401 fallback is sufficient.
- *Server-side session store (Redis / SQLite session table):* full revocation but new infra + more code. Overkill for V1.

**Why per-request status check:** ~1 SQL query per request. Already loading the user for `g.user.id` anyway, so essentially zero extra cost. Disabled-user attack window = 1 request, which is fine for "household" threat model.

### 6. Flask signed-cookie sessions, `Secure=<env-controlled>`

**Choice:** Flask's built-in `session` (signed by `FLASK_SECRET_KEY`, already in env). Cookie attributes: `HttpOnly=True`, `SameSite=Lax`, `Secure=<from SESSION_COOKIE_SECURE env var, default true>`.

**Alternatives considered:**
- *JWT in localStorage:* XSS risk + manual `Authorization` header on every axios call. SPAs without strong CSP shouldn't hold tokens in JS-readable storage.
- *Always `Secure=True`:* cleanest but breaks NAS HTTP entirely. Defer NAS HTTP to `nas-https` change while letting NAS continue to be the canonical instance during V1.
- *Auto-detect HTTPS via X-Forwarded-Proto:* footgun if reverse proxy isn't trustworthy. Explicit env var is more honest.

**Why explicit env:** NAS keeps working; cloud / future HTTPS NAS keeps default secure; no hidden trust assumptions.

### 7. Bootstrap admin via `INITIAL_ADMIN_EMAIL` + invite-URL-from-stdout (no `INITIAL_ADMIN_PASSWORD` in V1)

**Choice:** On first startup with empty `users` table, insert admin row + invite token; log invite URL to stdout. Admin reads `docker logs python-agent-api`, opens URL, sets password.

**Alternatives considered:**
- *`INITIAL_ADMIN_PASSWORD` env var shortcut:* avoids reading docker logs but adds a `must_change_password` flow + concern about env-stored plaintext password. Slim discussion dropped this.
- *Mastodon-style "first visitor becomes admin":* friendly but the user is the only first visitor; the env-driven explicit name is more deterministic.
- *Pre-seeded password = email or hardcoded:* security-bad.

**Why invite-URL-from-stdout:** it's exactly the same flow that family members go through. Admin tests their own onboarding flow on first deploy. Single code path.

### 8. Default landing after login is `/chat`, not `/wiki`

**Choice:** Frontend router's post-login redirect goes to `/chat` if no `?redirect=` query param. Currently the root path redirects to `/wiki`; this changes both the root redirect and the post-login redirect.

**Alternatives considered:**
- *Remember last-visited route:* requires localStorage state; over-engineered for V1.
- *Keep `/wiki` as default:* user explicitly preferred chat as the most-used view in mobile-friendly brainstorm.

**Why /chat:** matches user's stated mental model that ChatView is the killer feature. Knowledge browsing is a destination users navigate TO; chat is what they came for.

### 9. CLI invite tool (`python -m app.cli.invite_user`) ships in core, deletes when admin UI ships

**Choice:** Provide a CLI command for admin invites during the core change's lifetime. Replace it with the `multi-user-auth-admin-ui` change's HTTP endpoint + Vue UI.

**Alternatives considered:**
- *No CLI; admin uses raw SQL via `docker exec ... sqlite3`:* hostile UX. Token generation requires bcrypt-style logic that doesn't belong in raw SQL.
- *Skip the core/admin-ui split, ship admin UI in core:* the original plan. Adds ~250 lines and ~3 new files; user explicitly approved the split.
- *Keep CLI even after admin UI lands:* probably yes — useful for emergencies. But not blocking either change.

**Why CLI:** identical logic to the future HTTP endpoint, just minus the wrapping route. Tested by the same auth_service unit tests. ~30 lines of code. Pays off ten times over by enabling the split.

## Risks / Trade-offs

- **R-01 — Bootstrap admin lockout:** if admin loses the invite URL from logs AND the user table has the admin row but it's still `status='invited'`, every login fails. Recovery: `docker exec ... python -m app.cli.invite_user --resend austin.xyz@gmail.com`, regenerates token and prints new URL.
- **R-02 — `SESSION_COOKIE_SECURE=false` left set after `nas-https`:** cookies traverse plain HTTP unnecessarily. Mitigation: noted as a Pitfall in CLAUDE.md; `nas-https` change's tasks include "remove `SESSION_COOKIE_SECURE=false` from NAS .env".
- **R-03 — Disabled user keeps using stale cookie:** middleware's per-request status check kills them on next request. Worst case = whatever request they had in flight when disabled completes. Acceptable for family scale.
- **R-04 — Migration during in-flight requests:** if someone is mid-request while bootstrap migration is moving rows from `user_id='default'` to admin's UUID, the request might see partial state. Mitigation: bootstrap is fast (<1s for current data volume); accepting brief inconsistency on first-ever startup is fine. Subsequent startups skip the migration entirely.
- **R-05 — Google `sub` mismatch wrongly blocks legitimate user:** if a user's Google account is moved (rare), they'd 403. Mitigation: documented; admin disable + reinvite recovers them.
- **R-06 — argon2id verify is ~50ms per login:** acceptable for V1; not a DoS vector at family scale (no rate limit yet, but no public attack surface either since NAS is on LAN).
- **R-07 — Forgotten member password on NAS HTTP:** admin can't email a reset link (no SMTP). Mitigation V1: admin disable + reinvite the member. Hardening change can add a CLI / admin-UI password reset.

## Migration Plan

This is a frontend + backend change with a one-time bootstrap step. Ship sequence:

1. Implement schema migrations (idempotent `CREATE TABLE IF NOT EXISTS users`, `invite_tokens`).
2. Implement auth_service, user_service, middleware, all `/api/auth/*` routes; verify with pytest.
3. Add `@require_auth` + `g.user.id` to existing routes; verify existing pytest suite still green (mock g.user where tests don't go through auth).
4. Implement bootstrap migration; test against a fixture DB with `user_id='default'` rows.
5. Implement frontend: useAuthStore → LoginView → router guard → axios 401 → AcceptInviteView → ChangePasswordView → MeView → AppLayout user pill.
6. Implement CLI tool.
7. Run all suites: backend pytest, frontend vitest, Playwright (existing E2E specs need a `beforeEach` login fixture).
8. Live-test on dev stack with localhost (Google login works there).
9. Push image to Docker Hub.
10. Update NAS `.env` with `INITIAL_ADMIN_EMAIL`, `SESSION_COOKIE_SECURE=false`. UGOS Pull → Apply.
11. Read invite URL from `docker logs`, open in browser, set admin password, verify all 85 files / 30 entries / etc. visible.
12. Use CLI to invite a family member; verify their experience end-to-end.

**Rollback:** previous frontend image tag pinned in NAS docker-compose.yml. Schema changes are additive (new tables) — rolling back the image leaves the new tables present but unused, which is fine.

## Open Questions

None blocking. Soft items for follow-up:

1. **Q-01:** When a member changes their own password, should existing sessions on other devices be invalidated? V1 = no (no `session_version`); existing sessions stay valid until 30-day expiry. Hardening change addresses this.
2. **Q-02:** Should `/api/auth/me` cache the user object in memory for the request lifetime to avoid double DB lookups (one for `@require_auth`, one for `/me`'s response body)? Probably yes via `g.user` reuse. Minor optimization.
3. **Q-03:** When `nas-https` change lands, do we change the default landing back from `/chat` to `/wiki` if user requests? Track via user feedback.
