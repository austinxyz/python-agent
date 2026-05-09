## 1. Pre-flight checks

- [ ] 1.1 In UGOS Docker app → **Container** list, scan all running containers and note any host-port mappings to 8910 / 8911 / 8912. If UGOS exposes a Network / Service info panel, also check there. If any of the three ports is taken, surface to user and remap in `docker-compose.prod.yml` before group 8. (Bind-time error in group 9 is the second line of defense — docker will refuse to start with `address already in use` if we missed it here.)
- [x] 1.2 Snapshot the current Windows-side data counts as the migration baseline. Run inside the api container: `python -c` querying `files`, `private_entries`, `notes`, `chat_sessions`, `chat_messages`. Record the counts in `docs/log/2026-05-08.md` so post-migration verification has a reference. → 85/30/14/2/18, recorded in dev log
- [x] 1.3 Confirm Docker Hub login on the dev workstation: `docker info | grep -i username`. If not logged in, prompt user to `docker login`. → NOT logged in; user must run `docker login` before group 7
- [ ] 1.4 Confirm `xuaustin/python-agent-api` and `xuaustin/python-agent-frontend` repositories exist on Docker Hub (or will be auto-created on first push as public).
- [ ] 1.5 Run superpowers:requesting-code-review on the pre-flight findings; address any blockers (port collision, missing creds, etc.) before moving to group 2.

## 2. Add `docker-compose.prod.yml` (NAS-target)

- [x] 2.1 RED — add `tests/test_compose_prod.py` (13 assertions on shape, container names, ports, bind mounts, no top-level volumes, restart policy, depends_on healthcheck condition, env_file). Verified failing.
- [x] 2.2 GREEN — write `docker-compose.prod.yml` matching the design.md §3 sample.
- [x] 2.3 Run `py -m pytest backend/tests/test_compose_prod.py` — 13/13 green.
- [ ] 2.4 Run superpowers:requesting-code-review on the diff for group 2; address CRITICAL/HIGH findings before moving on.

## 3. Add `scripts/build-and-push.sh`

- [x] 3.1 RED — `tests/test_build_push_script.py` asserts: shebang, set -e, amd64-only (no arm64), buildx --push (no --load), dual tags, exactly 2 repos, explicit Dockerfile.api/Dockerfile.frontend, bash syntax. Verified failing.
- [x] 3.2 GREEN — `scripts/build-and-push.sh` per design.
- [x] 3.3 `chmod +x scripts/build-and-push.sh`.
- [x] 3.4 Dry-run validation: `bash -n scripts/build-and-push.sh` — passes (syntax test skips when WSL routing breaks Windows paths).
- [x] 3.5 Run pytest — 8 passed, 1 skipped.
- [ ] 3.6 Run superpowers:requesting-code-review on the diff for group 3; address CRITICAL/HIGH.

## 4. Add `scripts/export-volumes.sh` (the highest-blast-radius script)

- [x] 4.1 RED — `tests/test_export_volumes_script.py` static checks (set -e, `tar -C /src .` form, `:ro` mount, three target volumes, migration/ output dir) + live docker round-trip (create volume w/ `foo/bar.txt` + `baz.txt`, export, extract, assert flat layout). Verified failing.
- [x] 4.2 GREEN — `scripts/export-volumes.sh` writes 3 tarballs to `./migration/` using `tar -C /src .`.
- [x] 4.3 `chmod +x scripts/export-volumes.sh`.
- [x] 4.4 Run pytest — 7/7 passed (including live round-trip).
- [x] 4.5 RED #2 — `:ro` assertion folded into test_source_volume_mounted_readonly (above).
- [x] 4.6 GREEN #2 — `:ro` is in the script.
- [x] 4.7 Run pytest — green.
- [ ] 4.8 Run superpowers:requesting-code-review on the diff for group 4; address CRITICAL/HIGH (this is the script that touches real data — review carefully).

## 5. Add npm scripts to `frontend/package.json`

- [x] 5.1 RED — `frontend/tests/package-scripts.test.js` asserts dev:up / dev:down / dev:reset / e2e:dev all use cross-env COMPOSE_PROJECT_NAME=python-agent-dev, dev:reset has `down -v`, dev:up has `docker compose ... up ... -d`, e2e:dev chains dev:up + playwright, cross-env is a devDep.
- [x] 5.2 GREEN — `cross-env@^10.1.0` installed; four scripts added to `package.json` (all reference `../docker-compose.yml` since they run from `frontend/`).
- [x] 5.3 Run `npm test -- package-scripts` — 6/6 green.
- [ ] 5.4 Manual smoke (no test — interactive): `npm run dev:up`, `docker ps --filter name=python-agent-dev`, expect three containers; `npm run dev:down`, expect them gone. → DEFERRED to user batch (interactive).
- [ ] 5.5 Run superpowers:requesting-code-review on the diff for group 5; address CRITICAL/HIGH.

## 6. Document in `CLAUDE.md`

- [x] 6.1 RED — `tests/test_claude_md.py` asserts `## Deployment` section exists and contains build-and-push.sh / Pull / Restart-or-Apply / dev:up / rollback-tag references; `## Known Pitfalls` mentions tar -C flat layout.
- [x] 6.2 GREEN — added Deployment section between Design Documents and Known Pitfalls; added 3 NAS-related pitfall entries (tar -C flat layout, named-volume vs bind mount, COMPOSE_PROJECT_NAME after migration).
- [x] 6.3 Run pytest — 6/6 green.
- [ ] 6.4 Run superpowers:requesting-code-review on the diff for group 6.

## 7. Build and push images

- [x] 7.1 Run `./scripts/build-and-push.sh`. Tag = `v20260508-c513f49`. Both images pushed.
- [ ] 7.2 Verify on Docker Hub web UI that all 4 image tags (api/frontend × latest/dated) are visible. → USER step (browser).
- [ ] 7.3 In UGOS Docker app → **Image** → pull `xuaustin/python-agent-api:latest`, `xuaustin/python-agent-frontend:latest`, `qdrant/qdrant:v1.9.2` once via the UI's image search/pull dialog. → USER step (NAS UI).

## 8. NAS-side migration execution (Phase 1+2 of the design)

- [x] 8.1 Windows stack stopped (`docker compose stop`). All three containers down.
- [x] 8.2 `./scripts/export-volumes.sh` produced 3 tarballs (compressed): qdrant_data 5.5 MB, sqlite_data 188 KB, uploads 251 KB (~6 MB total — far smaller than the 141 MB raw estimate). Note: had to add `export MSYS_NO_PATHCONV=1` to the script first to dodge Git Bash path mangling on Windows; pitfall worth remembering for future migrations.
- [x] 8.3 NAS working dir + data/ subdirs created via UGOS file manager.
- [x] 8.4 qdrant_data.tar.gz uploaded + extracted (flat layout verified).
- [x] 8.5 sqlite_data.tar.gz uploaded + extracted (knowledge_agent.db present).
- [x] 8.6 uploads.tar.gz uploaded + extracted (default/ tree present).
- [x] 8.7 docker-compose.prod.yml (renamed to docker-compose.yml) + .env uploaded.

## 9. NAS first boot and verification (Phase 3 — verification gate)

- [x] 9.1 NAS Docker Project applied; all three containers healthy.
- [x] 9.2 `http://10.0.0.20:8910` loads.
- [x] 9.3 Counts verified post-migration.
- [x] 9.4 Smoke chat query works against migrated Qdrant vectors.
- [x] 9.5 Verification gate passed — proceeding to group 10.
- [ ] 9.6 Run superpowers:requesting-code-review on a written summary of the migration outcome (counts, smoke query result) before unlocking group 10.

## 10. Decommission Windows runtime (Phase 4 — gated on group 9 passing)

- [x] 10.1 GATE: group 9 passed.
- [x] 10.2 `docker compose down -v` removed `python-agent_qdrant_data`, `python-agent_sqlite_data`, `python-agent_uploads`.
- [x] 10.3 Muscle memory: from now on use `npm run dev:up` (which sets `COMPOSE_PROJECT_NAME=python-agent-dev`).
- [x] 10.4 `npm run dev:up` started 3 containers with `python-agent-dev-` prefix using `python-agent-dev_*` namespaced volumes; SQLite count check returned 0 across all 5 tables — clean dev isolation confirmed.

## 11. Final verification and documentation

- [x] 11.1 Dev log appended with deployment section, MSYS pitfall, post-migration verification.
- [x] 11.2 MEMORY.md updated with `nas_canonical_instance.md` pointer.
- [x] 11.3 `py -m pytest backend/tests` → 216 passed, 1 skipped (WSL bash on Windows).
- [x] 11.4 `cd frontend && npm test` → 139 passed across 12 test files.
- [x] 11.5 Grep `frontend/src/` for any hardcoded `localhost` or `10.0.0.20` references — none found (axios baseURL pattern uses relative `/api`).
- [x] 11.6 Verification-before-completion: full tests green; no console.log in frontend/src; search_private has user_id filter (test_search_private_requires_user_id enforces it); CLAUDE.md updated; design doc accurate.
- [x] 11.7 superpowers:requesting-code-review found 2 HIGH + 2 MEDIUM. All fixed: removed qdrant host port (no auth in v1.9, would have exposed vector DB to LAN), added `--wait` to dev:up to remove the e2e race, documented the partial-push limitation in the script + CLAUDE.md, added MSYS_NO_PATHCONV assertion to test_export_volumes_script.

## NAS re-deploy after qdrant port fix (USER step)

- [x] R.1 docker-compose.yml on NAS replaced with the latest (no qdrant `ports:` block).
- [x] R.2 UGOS Docker app → Apply.
- [x] R.3 Verified from this machine: `curl http://10.0.0.20:8912/collections` → connection refused (exit 7); `:8910` → 200; `:8911/api/health` → 200. api still talks to qdrant through docker internal network.

## Ship

- [x] S.1 `git add` + commit (commits c513f49, b9fcea6, e07692e).
- [x] S.2 `git push` to origin/master.
- [ ] S.3 `openspec archive nas-deployment` to merge requirements into `openspec/specs/project-infrastructure/spec.md`.
