## ADDED Requirements

### Requirement: NAS production compose file uses image refs and bind mounts
The repository SHALL include `docker-compose.prod.yml` at the project root, distinct from `docker-compose.yml`. The prod file MUST use `image:` refs (no `build:` sections), MUST bind-mount `./data/sqlite`, `./data/qdrant`, and `./data/uploads` into the api and qdrant containers, and MUST publish host ports `8910` (frontend) and `8911` (api). The qdrant service MUST NOT publish any host port (v1.9 has no auth; binding it to the LAN would expose the entire vector store). The file MUST NOT declare a top-level `volumes:` block. Container names MUST be set explicitly (`python-agent-frontend`, `python-agent-api`, `python-agent-qdrant`) so UGOS Docker Project UI lists them clearly. All three services MUST set `restart: unless-stopped`.

#### Scenario: NAS compose pulls images, doesn't build
- **WHEN** `docker compose -f docker-compose.prod.yml pull` is run on a fresh NAS
- **THEN** all three images (`xuaustin/python-agent-api:latest`, `xuaustin/python-agent-frontend:latest`, `qdrant/qdrant:v1.9.2`) are pulled from registries; no Dockerfile is invoked

#### Scenario: NAS bind mount paths exist relative to working dir
- **WHEN** `docker compose -f docker-compose.prod.yml up -d` is run with the working dir at `/volume1/docker/python-agent/`
- **THEN** the api container reads/writes to `/volume1/docker/python-agent/data/sqlite/knowledge_agent.db` on the host filesystem (visible in UGOS file manager)

#### Scenario: NAS host ports do not collide with default UGOS occupants
- **WHEN** the prod stack is started on UGREEN with default UGOS services running
- **THEN** ports 8910 and 8911 are unused before bind, and the stack starts without "address already in use" errors

#### Scenario: Qdrant is not reachable from the LAN
- **WHEN** the prod stack is running and a LAN device sends `curl http://10.0.0.20:8912/collections`
- **THEN** the connection is refused (no host listener) AND the api at 10.0.0.20:8911 still successfully queries qdrant via the docker internal network

### Requirement: Build script publishes amd64 images to Docker Hub
The repository SHALL include `scripts/build-and-push.sh` that builds linux/amd64 images for the api and frontend services and pushes them to Docker Hub under `xuaustin/python-agent-api` and `xuaustin/python-agent-frontend`. Each push MUST tag both `:latest` and `:vYYYYMMDD-<short-sha>` where the date is UTC and the sha is the current `git rev-parse --short HEAD`. The script MUST use `docker buildx` with the `multiarch` builder (auto-created if absent) and `--platform linux/amd64` (single arch). The script MUST exit non-zero on any build or push failure (`set -e`).

#### Scenario: Build script produces dual tags
- **WHEN** `./scripts/build-and-push.sh` is run on a clean working tree at commit `abc1234` on date 2026-05-08
- **THEN** Docker Hub receives `xuaustin/python-agent-api:latest`, `xuaustin/python-agent-api:v20260508-abc1234`, `xuaustin/python-agent-frontend:latest`, and `xuaustin/python-agent-frontend:v20260508-abc1234`

#### Scenario: Build failure stops the script
- **WHEN** the api Dockerfile contains a syntax error
- **THEN** the script exits non-zero before attempting the frontend build, and no partial latest tag is pushed

### Requirement: Three-environment isolation via COMPOSE_PROJECT_NAME
The system SHALL allow simultaneous local-dev and NAS-prod operation without volume conflicts. Local dev MUST run with `COMPOSE_PROJECT_NAME=python-agent-dev` so docker prefixes named volumes as `python-agent-dev_qdrant_data`, `python-agent-dev_sqlite_data`, and `python-agent-dev_uploads`. NAS prod uses bind-mount paths (no docker-managed volumes) and is therefore in a separate namespace by construction.

#### Scenario: Local dev volumes are namespaced
- **WHEN** `COMPOSE_PROJECT_NAME=python-agent-dev docker compose up -d` is run on the dev workstation
- **THEN** `docker volume ls` shows `python-agent-dev_qdrant_data`, `python-agent-dev_sqlite_data`, `python-agent-dev_uploads`, and the original `python-agent_*` volumes are unmodified

#### Scenario: Dev reset does not affect any NAS data
- **WHEN** `COMPOSE_PROJECT_NAME=python-agent-dev docker compose down -v` is run
- **THEN** only the `python-agent-dev_*` volumes are removed; the NAS at 10.0.0.20 sees no change to its bind-mounted data

### Requirement: NPM scripts wrap the dev stack lifecycle
`frontend/package.json` SHALL expose four scripts that abstract the COMPOSE_PROJECT_NAME convention so contributors don't need to remember to set the env var. The scripts MUST work on Windows (using `cross-env` to set the env var portably). The scripts:
- `dev:up` — starts the local dev stack (`COMPOSE_PROJECT_NAME=python-agent-dev docker compose up -d`)
- `dev:down` — stops it without volume removal
- `dev:reset` — stops and removes volumes (`down -v`), then starts fresh
- `e2e:dev` — ensures the dev stack is up before running Playwright tests

#### Scenario: dev:up starts the namespaced stack
- **WHEN** `npm run dev:up` is run from `frontend/`
- **THEN** the three containers are running with names prefixed `python-agent-dev-`

#### Scenario: dev:reset wipes only dev data
- **WHEN** `npm run dev:reset` is run
- **THEN** `python-agent-dev_*` volumes are removed, the stack is restarted fresh, and any NAS instance at 10.0.0.20 is untouched

#### Scenario: e2e:dev gates Playwright on the dev stack
- **WHEN** `npm run e2e:dev` is run with the dev stack already up
- **THEN** Playwright runs against `http://localhost:3000` (the dev stack), not against any other host

### Requirement: Volume export script produces flat-content tarballs
The repository SHALL include `scripts/export-volumes.sh` that, when run on a workstation with the legacy `python-agent_qdrant_data`, `python-agent_sqlite_data`, and `python-agent_uploads` volumes, produces three tarballs in `migration/` whose contents extract directly into a target bind-mount directory without nested subdirectories. The script MUST use `tar czf <archive> -C /src .` form (not `tar czf <archive> /src`). The script MUST mount source volumes read-only (`:ro`) to prevent accidental writes during export. The script MUST be idempotent — re-running overwrites existing tarballs.

#### Scenario: Export produces three tarballs with flat layout
- **WHEN** `./scripts/export-volumes.sh` is run on a workstation that has the three legacy volumes populated
- **THEN** `migration/qdrant_data.tar.gz`, `migration/sqlite_data.tar.gz`, and `migration/uploads.tar.gz` exist; extracting `qdrant_data.tar.gz` into a directory yields `collections/`, `raft_state.json`, etc. directly at the directory root (no `qdrant_data/` parent)

#### Scenario: Export does not modify source volumes
- **WHEN** the export script runs on volumes containing data D
- **THEN** after the script completes, the same volumes still contain exactly D (verified by content checksum)

### Requirement: Migration verification gate before Windows wipe
The system SHALL document an explicit Phase-3-before-Phase-4 gate in `tasks.md`: the Windows-side `docker compose down -v` step MUST appear after a verification step that confirms the NAS instance shows the expected post-migration data counts (85 files, 30 private entries, 14 notes, 2 chat sessions, 18 messages as of the migration date) and a smoke chat query returns sources from migrated content.

#### Scenario: Verification step precedes wipe in tasks.md
- **WHEN** a contributor reads `openspec/changes/nas-deployment/tasks.md`
- **THEN** the task that runs `docker compose down -v` on Windows appears strictly after a task that verifies the NAS counts and runs the smoke query, with both tasks marked unchecked initially

### Requirement: Daily NAS deployment workflow documented
`CLAUDE.md` SHALL gain a "## Deployment" section that documents (a) how to push a new image (`./scripts/build-and-push.sh`), (b) how to update the NAS via UGOS Docker Project UI (Pull → Restart, no ssh), (c) how to roll back by pinning a `:vYYYYMMDD-<sha>` tag in `docker-compose.yml` on the NAS, and (d) the local dev workflow using `npm run dev:up`. The "## Known Pitfalls" section SHALL gain at least one new entry covering migration-related lessons (e.g., the `tar -C /src .` flat-layout requirement) so future sessions don't repeat mistakes.

#### Scenario: New contributor finds deployment instructions
- **WHEN** a new contributor reads `CLAUDE.md` looking for "how do I update the NAS"
- **THEN** the answer is found in a "## Deployment" section with concrete commands and UI steps

#### Scenario: Migration pitfall captured for future sessions
- **WHEN** a future Claude session reads "## Known Pitfalls"
- **THEN** there is at least one entry mentioning the tarball flat-layout requirement (so the same mistake isn't made if migration is ever repeated)
