# NAS Deployment Design

**Date:** 2026-05-08
**Scope:** Deploy python-agent to UGREEN NAS (10.0.0.20), migrate existing Windows data, establish dev/prod isolation
**Goal:** Move the canonical instance off Windows onto the always-on NAS without losing the 85 files / 30 entries / 14 notes / 18 chat messages already accumulated, while keeping local development safe from accidentally polluting production data.

---

## Overview

Today python-agent runs only on the dev workstation (Windows, `docker-compose.yml` with build-in-place + named volumes). The NAS at 10.0.0.20 is always on, has Docker + docker-compose, and is the right home for the canonical instance.

This change establishes:
1. A registry-based image distribution flow (parallel to `growing`'s pattern), so updates are `pull && apply` from a NAS UI button.
2. A bind-mount-based prod compose file friendly to UGREEN's Docker Project UI.
3. A one-time data migration from Windows named volumes → NAS bind-mount directories.
4. A three-environment isolation model so local dev never writes to NAS data.

Multi-user isolation, cloud deployment, HTTPS, and application-level scheduled backups are explicitly **out of scope** for this round.

---

## Target Architecture

### NAS topology (10.0.0.20, UGREEN UGOS Pro, amd64)

```
┌─────────────────────────────────────────────────────────────┐
│  UGREEN NAS @ 10.0.0.20                                     │
│  Managed via UGOS Docker Project UI                         │
│                                                             │
│   python-agent-frontend  :8910 ← LAN entry point            │
│   python-agent-api       :8911                              │
│   python-agent-qdrant    :8912                              │
│                                                             │
│   Working dir: /volume1/docker/python-agent/                │
│     ├── docker-compose.yml    ← UI reads this               │
│     ├── .env                                                │
│     └── data/                                               │
│         ├── sqlite/           ← bind to api:/app/data       │
│         ├── qdrant/           ← bind to qdrant:/qdrant/...  │
│         └── uploads/          ← bind to api:/app/uploads    │
└─────────────────────────────────────────────────────────────┘
```

### Why these ports

`8910` / `8911` / `8912` form a memorable `891x` block, avoid common NAS occupants (5000 used by various web apps, 3000 sometimes Grafana), and stay outside the privileged range. Frontend is the only one most users hit; API and Qdrant ports are bound for debugging convenience but stay LAN-only.

### Why bind mounts (not named volumes) on NAS

UGREEN Docker Project UI (like Synology Container Manager) handles bind mounts much better than named volumes:
- Real folder paths visible in the file manager
- Backup = back up one directory tree
- Migration = drop tarballs into known paths
- Permission and ownership inspectable

The dev workstation keeps named volumes — bind mounts are NAS-specific.

### Why no HTTPS / reverse proxy this round

LAN-only, single user, internal network. Adding Caddy/Traefik would be infrastructure work disconnected from the actual deployment goal. When the project goes to cloud (after multi-user isolation lands), reverse proxy + HTTPS get added in that change.

---

## Image Distribution

### Repository naming

- `xuaustin/python-agent-api` — the Flask + LangGraph backend
- `xuaustin/python-agent-frontend` — Vue + nginx static bundle
- `qdrant/qdrant:v1.9.2` — official upstream, never forked

Each push tags both `:latest` and `:vYYYYMMDD-<short-sha>` so rollback is one tag swap away.

### Build script: `scripts/build-and-push.sh` (NEW)

Single-arch (linux/amd64) buildx, both images parallel-friendly:

```bash
#!/usr/bin/env bash
set -e
TAG="v$(date +%Y%m%d)-$(git rev-parse --short HEAD)"
DOCKER_USERNAME="xuaustin"

# Ensure buildx builder exists
docker buildx ls | grep -q multiarch || docker buildx create --name multiarch --use
docker buildx use multiarch

# api
docker buildx build --platform linux/amd64 \
  -t ${DOCKER_USERNAME}/python-agent-api:latest \
  -t ${DOCKER_USERNAME}/python-agent-api:${TAG} \
  -f Dockerfile.api --push .

# frontend
docker buildx build --platform linux/amd64 \
  -t ${DOCKER_USERNAME}/python-agent-frontend:latest \
  -t ${DOCKER_USERNAME}/python-agent-frontend:${TAG} \
  -f Dockerfile.frontend --push .

echo "Pushed ${TAG}"
```

No multi-arch (UGREEN is amd64; future cloud will likely be amd64 too).

Free-tier Docker Hub allows 1 private repo. Both images are personal and could go public — they contain no secrets (config + dependencies). Default to **public** unless a concrete reason to keep private appears.

### Two compose files (clear separation of concerns)

| File | Used by | Volumes | Image source |
|------|---------|---------|--------------|
| `docker-compose.yml` (existing) | Local dev on Windows | named volumes (`*_data`) | `build:` from local Dockerfiles |
| `docker-compose.prod.yml` (NEW) | NAS via UGOS UI | bind mounts (`./data/*`) | `image:` from Docker Hub |

The prod compose is what gets uploaded to the NAS working dir.

### `docker-compose.prod.yml` (NEW, NAS-target)

```yaml
services:
  qdrant:
    image: qdrant/qdrant:v1.9.2
    container_name: python-agent-qdrant
    restart: unless-stopped
    ports:
      - "8912:6333"
    volumes:
      - ./data/qdrant:/qdrant/storage
    healthcheck:
      test: ["CMD-SHELL", "bash -c 'echo > /dev/tcp/localhost/6333'"]
      interval: 10s
      timeout: 5s
      retries: 5
      start_period: 15s

  api:
    image: xuaustin/python-agent-api:latest
    container_name: python-agent-api
    restart: unless-stopped
    ports:
      - "8911:5000"
    env_file: .env
    volumes:
      - ./data/sqlite:/app/data
      - ./data/uploads:/app/uploads
    depends_on:
      qdrant:
        condition: service_healthy

  frontend:
    image: xuaustin/python-agent-frontend:latest
    container_name: python-agent-frontend
    restart: unless-stopped
    ports:
      - "8910:3000"
    depends_on:
      - api
```

No top-level `volumes:` declaration — bind mounts don't need it.

---

## Three-Environment Isolation

| Environment | Where | Volumes | Compose project name | Real data? |
|-------------|-------|---------|----------------------|-----------|
| **Production** | NAS 10.0.0.20 | bind: `/volume1/docker/python-agent/data/*` | (UI-managed) | ✓ canonical |
| **Local dev stack** | Windows | named: `python-agent-dev_*` | `python-agent-dev` | ✗ throwaway |
| **Tests** | local pytest / vitest / Playwright | tmp_path, mocks, dev stack | (none / dev stack) | ✗ |

### How the local dev stack stays separate

```bash
# Daily dev — completely independent from NAS
COMPOSE_PROJECT_NAME=python-agent-dev docker compose up -d
# Volumes: python-agent-dev_qdrant_data, python-agent-dev_sqlite_data, python-agent-dev_uploads
# URL: http://localhost:3000
```

Same compose file, different project name → docker auto-namespaces volume names with the project prefix. No risk of collision.

Reset whenever:
```bash
COMPOSE_PROJECT_NAME=python-agent-dev docker compose down -v
```

### Test isolation

- **`backend/tests/` (pytest)** — already uses `tmp_path` fixtures, in-memory SQLite, `MagicMock` for Qdrant. Doesn't touch any docker volume regardless of what's running. Green ↔ NAS state is fully decoupled.
- **`frontend/tests/` (vitest)** — happy-dom + faked stores. No network.
- **`frontend/e2e/` (Playwright)** — sends real HTTP to a backend. Config pinned to `http://localhost:3000` and never points at the NAS. The `__e2e_*` title prefix + `afterEach` cleanup is a second line of defense; the primary defense is "Playwright never knows the NAS exists."

### Optional: occasional debug against real data

Sometimes a bug only reproduces with real data. `scripts/snapshot-from-nas.sh` (NEW, future) will:
1. SSH to NAS, tar the three `data/` subdirs into `/tmp`
2. scp to dev workstation
3. Pour into `python-agent-dev_*` named volumes (overwriting current dev data)

Strictly one-way, NAS → dev. Never the other direction.

---

## One-Time Data Migration

### Pre-migration data audit (already taken on 2026-05-08)

| Table / Volume | Count / Size |
|----------------|--------------|
| `files` | 85 rows |
| `private_entries` | 30 rows |
| `notes` | 14 rows |
| `chat_sessions` | 2 rows |
| `chat_messages` | 18 rows |
| `python-agent_qdrant_data` | 140 MB |
| `python-agent_sqlite_data` | 647 KB |
| `python-agent_uploads` | 586 KB |
| **Total** | **~141 MB to transfer** |

### Step-by-step procedure

**Phase 1 — Windows (CLI; this is the dev workflow you already use):**

1. Stop the running stack (do NOT `down -v`):
   ```bash
   docker compose stop
   ```

2. Run `scripts/export-volumes.sh` (NEW) to produce three tarballs:

   ```bash
   #!/usr/bin/env bash
   set -e
   mkdir -p migration
   for V in qdrant_data sqlite_data uploads; do
     docker run --rm \
       -v python-agent_$V:/src:ro \
       -v "$(pwd)/migration:/dest" \
       alpine tar czf /dest/${V}.tar.gz -C /src .
     echo "exported migration/${V}.tar.gz"
   done
   ```

   Critical: the `-C /src .` form tars the *contents* of /src, not the dir itself, so extraction puts files at the target root, not in a nested subdir.

**Phase 2 — NAS (UI):**

3. UGOS file manager: navigate to (or create) `/volume1/docker/python-agent/`. Inside it create:
   - `data/sqlite/`
   - `data/qdrant/`
   - `data/uploads/`
4. Upload `qdrant_data.tar.gz` → `data/qdrant/`. Right-click → **Extract here**. Delete the tarball.
5. Upload `sqlite_data.tar.gz` → `data/sqlite/`. Extract here. Delete.
6. Upload `uploads.tar.gz` → `data/uploads/`. Extract here. Delete.
7. Upload the prepared `docker-compose.yml` (the prod variant) and `.env` to `/volume1/docker/python-agent/`.

**Phase 3 — Boot and verify:**

8. UGOS Docker app → Project → New → working dir `/volume1/docker/python-agent/` → UI auto-detects `docker-compose.yml` → Apply. UI pulls `xuaustin/python-agent-api:latest`, `xuaustin/python-agent-frontend:latest`, `qdrant/qdrant:v1.9.2`, then starts the three containers.
9. Browser: `http://10.0.0.20:8910`. Verify:
   - 85 files visible in /ingest tree
   - 30 private entries in /private
   - 14 notes
   - 2 chat sessions with their 18 messages
10. Smoke query: ask the FBAR/FATCA question. Verify the same 11 sources surface (proves Qdrant vectors moved cleanly).

**Phase 4 — Decommission Windows runtime (only after Phase 3 fully verified):**

11. `docker compose down -v` on Windows to wipe the now-stale named volumes.
12. From now on, Windows uses **only** the `python-agent-dev` project name for any docker-compose work.

### Permissions note

The api image runs as root (no `USER` directive in `Dockerfile.api`), so bind-mounted directories are writable without `chown`. If a future change introduces a non-root user, this design needs a `chown -R <uid>:<gid> data/` step in Phase 2.

### Rollback

- Failure during Phase 2: nothing on NAS is live yet — re-extract or re-upload as needed.
- Failure during Phase 3: stop the project in UI, fix the issue (e.g., wrong .env, image pull failure), Apply again.
- Critical failure after Phase 4 (Windows volumes already wiped): pull last `:vYYYYMMDD-...` image tag known to work; if data corruption, restore from a NAS-level snapshot (covered by NAS native backup, not this design).

---

## Daily Workflows After Migration

### Update production (after pushing new image)

1. On dev workstation: `./scripts/build-and-push.sh`
2. NAS UI → Docker → Project → python-agent → **Pull** (refreshes `:latest` tags) → **Restart**
3. Verify in browser. If broken, edit `docker-compose.yml` to pin the previous `:vYYYYMMDD-<sha>` tag, Pull, Restart.

### Local dev iteration

```bash
# First time
COMPOSE_PROJECT_NAME=python-agent-dev docker compose up -d

# Iterate code, then
docker cp backend/app/<changed_file>.py python-agent-dev-api-1:/app/app/<changed_file>.py
docker restart python-agent-dev-api-1
# (frontend changes still need a docker compose -p python-agent-dev up --build -d frontend)
```

### NPM script shortcuts (NEW, frontend/package.json additions)

- `npm run dev:up` → `cross-env COMPOSE_PROJECT_NAME=python-agent-dev docker compose up -d`
- `npm run dev:down` → `cross-env COMPOSE_PROJECT_NAME=python-agent-dev docker compose down`
- `npm run dev:reset` → `cross-env COMPOSE_PROJECT_NAME=python-agent-dev docker compose down -v && npm run dev:up`
- `npm run e2e:dev` → ensures dev stack is up, then `playwright test`

---

## File Inventory (what this change adds)

| File | Status | Purpose |
|------|--------|---------|
| `docker-compose.prod.yml` | NEW | NAS-target compose (bind mounts, image refs, port 891x) |
| `scripts/build-and-push.sh` | NEW | buildx amd64 + Docker Hub push for both images |
| `scripts/export-volumes.sh` | NEW | One-time tarball export from Windows named volumes |
| `frontend/package.json` | MODIFIED | Add `dev:up` / `dev:down` / `dev:reset` / `e2e:dev` scripts |
| `docs/superpowers/specs/2026-05-08-nas-deployment-design.md` | NEW (this file) | Design doc |
| `docs/log/2026-05-08.md` | MODIFIED | Append deployment section after migration completes |
| `CLAUDE.md` | MODIFIED | Add "## Deployment" section with NAS workflow notes + new pitfalls |

No changes to backend code, no changes to frontend code, no schema changes.

---

## Risks and Mitigations

| Risk | Mitigation |
|------|------------|
| Tarball extract via UI on NAS produces wrong directory layout | `-C /src .` form was chosen specifically to extract flat. Verified by inspecting an existing extracted output before kicking off the live migration. |
| Permission mismatch (container can't write bind-mounted dir) | api image runs as root; verified. Documented as future risk if non-root user is added. |
| Port collision on NAS | `ss -tlnp` check in tasks.md before deploying; ports `891x` chosen to avoid known NAS occupants. |
| `.env` accidentally committed or exposed | `.env` continues to be gitignored; uploaded directly to NAS via UI, never committed. |
| Docker Hub image pull fails on NAS (rate limit / network) | Public images bypass auth; rate limit is ~100 pulls/6h for unauthenticated, plenty for personal use. If hit, log into Docker Hub from NAS UI. |
| Windows wipe (Phase 4) before NAS is fully verified | Phase 4 explicitly requires Phase 3 verification first. Document in tasks.md as a checklist gate. |
| Qdrant version drift between Windows and NAS | Both pin `qdrant/qdrant:v1.9.2`. No drift possible. |

---

## Out of Scope (deferred)

- **Multi-user isolation** — explicitly the gating change for cloud. Lives in a separate future change.
- **Cloud deployment** — depends on multi-user isolation. Probably Railway or Fly.io when it happens.
- **HTTPS / reverse proxy** — only meaningful when going public.
- **Application-level scheduled backup** — UGOS native volume snapshots cover this for V1; revisit only after a real recovery incident or when the NAS leaves the picture.
- **Github Actions CI/CD** — `./scripts/build-and-push.sh` is fine for personal pace. Automate when push frequency justifies it.
- **Snapshot-from-NAS dev refresh script** — useful but not blocking; build it when the first "I need to debug against real data" situation arises.
- **Monitoring / alerting** — UGOS Docker UI shows container health; that's enough at single-user scale.

---

## Open Questions

None blocking. Two soft items to revisit later:

1. Whether to use Github Actions for image builds — defer until manual cadence becomes annoying.
2. Whether to use Watchtower or similar for automatic image updates on NAS — probably not, manual control is preferable for this stage.
