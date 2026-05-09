## Why

Today python-agent only runs on the dev workstation (Windows, build-in-place). The 85 files / 30 private entries / 14 notes / 18 chat messages already accumulated are trapped on a machine that gets shut down every night, while the always-on UGREEN NAS at `10.0.0.20` is the right home for the canonical instance. We need a deployment path that (a) gets the data over without losing anything, (b) keeps day-to-day dev work from accidentally writing to real data, and (c) is ergonomic to update from the NAS UI without ssh.

## What Changes

- Introduce a registry-based image distribution: `xuaustin/python-agent-api` and `xuaustin/python-agent-frontend` published to Docker Hub via a new `scripts/build-and-push.sh` (single-arch linux/amd64; UGREEN is amd64).
- Add `docker-compose.prod.yml` (NAS-target) that uses `image:` refs (no local builds), bind mounts to `./data/{sqlite,qdrant,uploads}`, and host ports `8910/8911/8912` to avoid common NAS occupants. Existing `docker-compose.yml` stays as-is for local dev.
- Migrate the three Windows named volumes (`qdrant_data` 140 MB, `sqlite_data` 647 KB, `uploads` 586 KB) to NAS bind-mount directories one time, via tarballs uploaded + extracted through the UGOS file manager (no ssh required).
- Establish a three-environment isolation model: prod on NAS (canonical), local dev stack via `COMPOSE_PROJECT_NAME=python-agent-dev` (fully separate volume namespace), tests via existing `tmp_path` / mocks / Playwright-against-localhost. Add `npm run dev:up | dev:down | dev:reset | e2e:dev` shortcuts to the frontend package.
- Document the daily NAS update workflow (UI → Pull → Restart) and the rollback path (pin `:vYYYYMMDD-<sha>` tag) in `CLAUDE.md`.

No backend code changes. No frontend code changes. No schema changes.

## Capabilities

### New Capabilities
None.

### Modified Capabilities
- `project-infrastructure`: extends the existing single-compose definition to cover (a) a prod compose variant for NAS that uses image refs + bind mounts + remapped host ports, (b) the registry image distribution flow, (c) the one-time data migration procedure, and (d) the three-environment volume isolation pattern. Adds new requirements; does not remove or weaken existing ones.

## Impact

- **Files added**: `docker-compose.prod.yml`, `scripts/build-and-push.sh`, `scripts/export-volumes.sh`.
- **Files modified**: `frontend/package.json` (4 new npm scripts), `CLAUDE.md` (deployment section + new pitfalls).
- **External dependencies**: Docker Hub account (`xuaustin/*` repos, public). No new code dependencies.
- **Operational**: One-time migration window with the dev workstation stopped; afterward the NAS is the canonical instance and the Windows machine runs only the `python-agent-dev` project.
- **Out of scope** (deferred): multi-user isolation, cloud deployment, HTTPS/reverse proxy, application-level scheduled backup (NAS-native volume snapshots cover V1), CI/CD automation. See design.md §"Out of Scope".

Design document already brainstormed and committed to git: `docs/superpowers/specs/2026-05-08-nas-deployment-design.md` (commit `66d71da`).
