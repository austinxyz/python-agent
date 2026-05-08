## Context

The full architectural reasoning lives in `docs/superpowers/specs/2026-05-08-nas-deployment-design.md` (committed `66d71da`). This file captures the decisions and their alternatives so future readers see *why* each choice was made.

Current state:
- Single `docker-compose.yml` builds in-place on the dev workstation. Three named volumes (`python-agent_qdrant_data` 140 MB, `python-agent_sqlite_data` 647 KB, `python-agent_uploads` 586 KB) hold real data.
- Reference deployment exists at `C:\Users\lorra\projects\growing\` — Spring Boot service + Vue frontend + cron backup, distributed via `xuaustin/*` Docker Hub images and pulled on the NAS. We're adopting the same image-distribution shape but adapting for SQLite + Qdrant (instead of external MySQL) and for UGREEN's Docker Project UI (instead of pure CLI).

Constraints:
- UGREEN NASync runs UGOS Pro (amd64). Docker + docker-compose + ssh available, but the user wants to manage day-to-day deploys via the UI, not ssh.
- LAN-only, single user. Multi-user isolation is the gating change for cloud (out of scope here).
- Real data on Windows must not be lost during migration. Migration window of ~10 minutes is acceptable.

## Goals / Non-Goals

**Goals:**
- Move the canonical instance to NAS without data loss.
- Day-to-day deploys: NAS UI button (Pull → Restart), no ssh.
- Local dev work cannot accidentally write to NAS data.
- Rollback to a known-good image tag is one config edit.

**Non-Goals:**
- Multi-user isolation (separate future change; gates cloud).
- Cloud deployment (separate future change; depends on multi-user).
- HTTPS / reverse proxy (only meaningful when public).
- Application-level scheduled backups — UGOS native volume snapshots cover V1 risk profile.
- Github Actions / CI image builds — manual `./scripts/build-and-push.sh` is fine at personal cadence.

## Decisions

### 1. Bind mounts on NAS, named volumes on dev workstation

**Choice:** Two compose files. `docker-compose.yml` (existing, dev) keeps named volumes. New `docker-compose.prod.yml` (NAS) uses bind mounts to `./data/{sqlite,qdrant,uploads}` under the working dir.

**Alternatives considered:**
- *Named volumes on NAS too*: closer to the dev shape, but the UGOS Docker Project UI handles named volumes poorly (data not visible in file manager, awkward to back up, awkward to migrate).
- *Bind mounts on dev too*: would force a project-specific directory on Windows, breaks the existing `docker compose down -v` reset shortcut, and offers no benefit when there's no UI involved.
- *Single compose file with profiles*: tempting (DRY), but the volume shape (`./data/qdrant` bind vs `qdrant_data` named volume) cannot be expressed as a profile-conditional in compose v3. Two files is simpler than templating.

**Why two files wins:** clear separation of "dev runtime" vs "what the NAS sees," and matches the growing precedent.

### 2. Single-arch (linux/amd64) build, not multi-arch

**Choice:** `scripts/build-and-push.sh` builds only `linux/amd64`.

**Alternatives considered:**
- *Multi-arch (amd64 + arm64)* like growing's `build-multiarch.sh`: would future-proof for ARM clouds (Graviton, Ampere) but adds ~3-5 min per build and isn't useful for the current target.
- *Native build per host* (build on dev, build on NAS): would skip the registry entirely but loses tag history and rollback ergonomics.

**Why amd64-only wins:** UGREEN is amd64; future cloud (Railway/Fly) will most likely also be amd64; pivoting to multi-arch is a one-line change in the script when needed.

### 3. UI-driven migration with tar archives

**Choice:** Export the three Windows volumes as tar.gz, upload via the UGOS file manager, right-click "Extract here" into the prepared `data/{sqlite,qdrant,uploads}` directories.

**Alternatives considered:**
- *ssh + scp + manual extract*: works but the user explicitly wants UI-only on the NAS side.
- *rsync over ssh* directly volume → bind-mount-dir: faster for incremental updates, but this is a one-time cutover; the UI-extract approach is fine for ~141 MB total.
- *Set up a temporary file server on NAS and pull*: more moving parts, no benefit.

**Critical detail:** the export script uses `tar -C /src .` (not `tar /src`) so the archive contains only the contents — extraction at the target directory yields a flat layout, not a nested `qdrant_data/` subdirectory.

### 4. Three-environment isolation via `COMPOSE_PROJECT_NAME`

**Choice:** Local dev runs the same `docker-compose.yml` but with `COMPOSE_PROJECT_NAME=python-agent-dev`, which prefixes every named volume with `python-agent-dev_`. NAS bind mounts are namespaced by directory path.

**Alternatives considered:**
- *Separate compose file for dev*: would duplicate the build-and-run config. Same shape was already working; just rename the project.
- *Environment-specific Dockerfile.dev / Dockerfile.prod*: solves a problem we don't have (dev and prod images are the same).

**Why this wins:** zero new config, just an env var. Built into compose. Reset is `docker compose -p python-agent-dev down -v`.

### 5. Ports remapped to `8910/8911/8912` on NAS

**Choice:** frontend `8910`, api `8911`, qdrant `8912`. Local dev keeps `3000/5000/6333`.

**Alternatives considered:**
- *Same ports as dev (3000/5000/6333)*: simpler memory, but `5000` collides with several common UGREEN add-on apps (Portainer alternatives, etc.) and `3000` sometimes collides with Grafana on NAS.
- *Privileged ports (80/443)*: would conflict with UGOS web admin and require HTTPS termination, neither of which we're doing.

**Why `891x` wins:** a memorable block, low collision risk, and clearly identifies the project at a glance.

### 6. Public Docker Hub repos

**Choice:** Default `xuaustin/python-agent-api` and `xuaustin/python-agent-frontend` to public.

**Alternatives considered:**
- *Private repos*: free tier allows 1 private; this project would consume it. The images contain only build artifacts and pip-installed dependencies — no secrets, no proprietary code (the source is already on a public Github repo).
- *GHCR or other registry*: extra account / config, no upside at this scale.

**Why public wins:** no rate-limit auth on pulls (the NAS pulls without login), no $$ if a second project ever needs the private slot, and a public image is consistent with a public source repo.

### 7. No application-level backup this round

**Choice:** Rely on UGOS native volume snapshots.

**Alternatives considered:**
- *Add a backup container modeled on growing's `backup` service*: tar `data/` daily, retain 7/4/12 (daily/weekly/monthly). Real value but real complexity (cron container, retention logic, manual-trigger endpoint). Defer until either (a) UGOS snapshots prove insufficient, or (b) we move off the NAS.

**Why deferring wins:** the NAS already provides the same protection at the storage layer. Don't build infrastructure for risks already mitigated elsewhere.

## Risks / Trade-offs

- **Tarball extract layout wrong** → spot-check the first extraction (qdrant) before doing sqlite + uploads; if directory structure is wrong, restart from Phase 2.
- **Permission mismatch on bind-mounted dirs** → api image runs as root (verified: `Dockerfile.api` has no `USER` directive), so writes succeed without `chown`. Future risk if non-root user is added.
- **Port collision on NAS at deploy time** → `ss -tlnp | grep -E ':(8910|8911|8912)\b'` check is the first task; remap in `docker-compose.prod.yml` if any are taken.
- **Docker Hub pull fails on NAS** → most often rate-limit (~100 unauthenticated pulls / 6h). Mitigation: log into Docker Hub from UGOS Docker UI once.
- **Phase 4 (Windows wipe) before NAS verified** → procedural gate in `tasks.md` requires Phase 3 verification before Phase 4 runs.
- **Qdrant version drift Windows → NAS** → both compose files pin `qdrant/qdrant:v1.9.2`; no upgrade path included in this change.

## Migration Plan

See `tasks.md` for the step-by-step task list. Summary:

1. Build infrastructure (compose files, scripts, npm shortcuts) and TDD-verify the export script against an empty volume locally.
2. Build + push `:latest` and `:vYYYYMMDD-<sha>` images to Docker Hub.
3. Stop Windows runtime, run `export-volumes.sh`, get three tarballs.
4. UGOS UI: prepare working dir, upload tarballs, extract, upload `docker-compose.yml` + `.env`, Apply project.
5. Verify counts (85/30/14/2/18) and run a smoke query.
6. Wipe Windows volumes; rename future Windows compose runs to use `COMPOSE_PROJECT_NAME=python-agent-dev`.

**Rollback strategy:**
- Pre-Phase-4: Windows volumes still intact; just stop NAS containers and restart Windows.
- Post-Phase-4: pull last-good `:vYYYYMMDD-<sha>` tag in NAS UI; if data corruption, restore from UGOS snapshot.

## Open Questions

None blocking. Two soft items to revisit later:
1. Github Actions for image builds — defer until manual cadence becomes annoying.
2. Watchtower for auto-update on NAS — probably not; manual control preferable at this stage.
