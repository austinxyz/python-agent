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

- [ ] 7.1 Run `./scripts/build-and-push.sh`. Confirm the tag is `vYYYYMMDD-<git short sha>` of the current HEAD.
- [ ] 7.2 Verify on Docker Hub web UI that all 4 image tags (api/frontend × latest/dated) are visible and the size is reasonable (api ~570 MB compressed-layer, frontend ~70 MB).
- [ ] 7.3 In UGOS Docker app → **Image** → pull `xuaustin/python-agent-api:latest`, `xuaustin/python-agent-frontend:latest`, `qdrant/qdrant:v1.9.2` once via the UI's image search/pull dialog. Confirms image visibility and saves Apply time in group 9. If a pull is rate-limited, log into Docker Hub via UGOS Docker UI's registry settings.

## 8. NAS-side migration execution (Phase 1+2 of the design)

- [ ] 8.1 On Windows: `docker compose stop` (NOT `down -v` — keep volumes). Verify with `docker compose ps`.
- [ ] 8.2 Run `./scripts/export-volumes.sh`. Verify three tarballs in `migration/`: roughly 140 MB / 700 KB / 600 KB.
- [ ] 8.3 In UGOS file manager: navigate to the project working dir (e.g., `/volume1/docker/python-agent/`). Create empty subdirectories `data/sqlite/`, `data/qdrant/`, `data/uploads/`.
- [ ] 8.4 Upload `qdrant_data.tar.gz` to `data/qdrant/`. Right-click → **Extract here**. After extraction, delete the tarball. Verify the layout is flat (e.g., `data/qdrant/collections/` exists, NOT `data/qdrant/qdrant_data/collections/`).
- [ ] 8.5 Upload `sqlite_data.tar.gz` to `data/sqlite/`. Extract. Delete tarball. Verify `data/sqlite/knowledge_agent.db` exists.
- [ ] 8.6 Upload `uploads.tar.gz` to `data/uploads/`. Extract. Delete tarball. Verify `data/uploads/default/` exists.
- [ ] 8.7 Upload `docker-compose.prod.yml` (renamed to `docker-compose.yml` in the NAS working dir) and a fresh `.env` (copied from Windows) to `/volume1/docker/python-agent/`.

## 9. NAS first boot and verification (Phase 3 — verification gate)

- [ ] 9.1 In UGOS Docker app: Project → New → working dir `/volume1/docker/python-agent/` → Apply. Wait for all three containers to reach healthy status.
- [ ] 9.2 Browser open `http://10.0.0.20:8910`. Confirm UI loads.
- [ ] 9.3 Verify counts via UI: 85 files in /ingest, 30 entries in /private, 14 notes, 2 chat sessions with 18 total messages combined. (Counts taken from task 1.2.)
- [ ] 9.4 Smoke chat query: ask "我更新了很多个人信息，你再看看我需要怎么处理FBAR/FATCA" with private scope on. Confirm the response cites `绿卡放弃 vs 保留分析` (proves Qdrant vectors moved cleanly).
- [ ] 9.5 If any verification fails, STOP. Do NOT proceed to group 10. Diagnose, restart from the failing step.
- [ ] 9.6 Run superpowers:requesting-code-review on a written summary of the migration outcome (counts, smoke query result) before unlocking group 10.

## 10. Decommission Windows runtime (Phase 4 — gated on group 9 passing)

- [ ] 10.1 **GATE:** Confirm group 9 fully passed (all four verification checks green). If anything in group 9 is unchecked, do not proceed.
- [ ] 10.2 On Windows: `docker compose down -v` to remove the now-stale `python-agent_*` named volumes.
- [ ] 10.3 Update local muscle memory: from now on, all local docker-compose work uses `COMPOSE_PROJECT_NAME=python-agent-dev` (or the new `npm run dev:*` scripts).
- [ ] 10.4 Run `npm run dev:up`, verify the dev stack starts on `localhost:3000` with empty data (sanity check the isolation worked).

## 11. Final verification and documentation

- [ ] 11.1 Update `docs/log/2026-05-08.md` with a deployment section: deployment workflow, post-migration counts, rollback recipe, dev/prod separation in practice.
- [ ] 11.2 Update `MEMORY.md` (if relevant) — likely add a memory pointing at the design doc and noting the project is now NAS-canonical.
- [ ] 11.3 Run `cd backend && pytest` (full suite — should still be 182 green; nothing in this change touches application code).
- [ ] 11.4 Run `cd frontend && npm test` (vitest full suite, including the new package-scripts test).
- [x] 11.5 Grep `frontend/src/` for any hardcoded `localhost` or `10.0.0.20` references — none found (axios baseURL pattern uses relative `/api`).
- [ ] 11.6 Run superpowers:verification-before-completion: full test suite pass; no console.log in frontend/src; private collection queries still include user_id filter (grep `qdrant.search.*private` and verify filter present); CLAUDE.md updated; design doc still matches reality.
- [ ] 11.7 Final superpowers:requesting-code-review on the entire change diff.

## Ship

- [ ] S.1 `git add` all new files + modified ones; commit with `feat: NAS deployment — image distribution, prod compose, data migration` style message.
- [ ] S.2 `git push` to origin/master.
- [ ] S.3 `openspec archive nas-deployment` to merge requirements into `openspec/specs/project-infrastructure/spec.md`.
