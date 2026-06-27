# OpenSpec + Superpowers Workflow

**Status:** Active (as of 2026-05-10; last updated 2026-06-26)
**Schema:** `superpowers-driven` — installed at user-level via `opsx-superpowers` plugin (`opsx-install`)
**Plugin repo:** `github.com/austinxyz/opsx-superpowers` (commands + schema + templates)
**Slash commands:** `.claude/commands/opsx/{explore,propose,apply,archive}.md` (synced from plugin)

## TL;DR

Every change in this repo goes through 4 phases:

```
/opsx:explore <topic>   → docs/superpowers/specs/<date>-<topic>-requirements.md
       (5 phases: free-think → draft → review → UI mocks → commit)

/opsx:propose <topic>   → openspec/changes/<topic>/{proposal,specs,design,tasks}.md
       (Status: REVIEWED gate; --schema superpowers-driven)

/opsx:apply <topic>     → executes tasks.md with CONTRACT/EVAL harness
       (each group: N.0 CONTRACT → RED/GREEN → N.E EVAL subagent → FIX loop → final verification)

/opsx:archive <topic>   → openspec/changes/archive/<date>-<topic>/ + 4 cleanups
       (capability ## Purpose; specs README; CLAUDE.md; project README; dev log)
```

## Why this exists

The `multi-user-auth-core` change exercised every step end-to-end on 2026-05-10. It exposed gaps: deferred code reviews almost shipped, the auto-generated capability spec had `## Purpose: TBD`, mocks lived by convention not by enforcement, and the agent had to re-discover the workflow rules in 4 different files. This schema + the 4 rewritten slash commands lock the workflow down so future changes can't drop these steps.

## Where to read more

- **Design doc** (the why and the architecture): `docs/superpowers/specs/2026-05-10-openspec-superpowers-workflow-design.md`
- **Plugin design**: `docs/superpowers/specs/2026-05-11-opsx-superpowers-plugin-design.md`
- **Schema definition**: `opsx-superpowers` plugin → `schemas/superpowers-driven/schema.yaml` (user-level after `opsx-install`)
- **Per-phase command definitions**: `.claude/commands/opsx/<phase>.md` (synced from plugin)
- **Project context (tech stack, paths, conventions)**: `openspec/config.yaml`

## Phase 1: `/opsx:explore`

5 phases inside one command. The agent walks them in order.

1. Free-thinking (existing explore stance — read code, ASCII diagrams, follow threads)
2. Draft requirements (`Status: DRAFT` at `docs/superpowers/specs/<date>-<topic>-requirements.md`)
3. Brainstorming review pass (placeholder / consistency / scope / ambiguity); flips to `Status: REVIEWED`
4. UI side-trip (only if `HAS_UI_SURFACE: yes`): `awesome-design-md` style + Visual Companion mocks → HTML at `docs/superpowers/specs/mocks/<date>-<topic>-mocks.html`
5. Commit + handoff

Anti-pattern guard: the command refuses to auto-trigger `/opsx:propose`. The user must invoke it explicitly.

## Phase 2: `/opsx:propose`

Pre-flight: `Status: REVIEWED` requirements doc must exist. Refuses on `DRAFT`.

Steps: `openspec new change --schema superpowers-driven` → walk artifacts in dependency order → branch on `HAS_UI_SURFACE` for mocks (real vs stub) → commit.

Output: `openspec/changes/<topic>/{proposal,specs,design,tasks}.md` plus the requirements doc and mocks file (already at `docs/superpowers/specs/`).

## Phase 3: `/opsx:apply`

Reads context (proposal, specs, design, mocks, requirements). Invokes `superpowers:test-driven-development` at session start. Walks tasks with CONTRACT/EVAL harness:

- **`N.0 CONTRACT`** → write `contracts/group-N.md` (Spec / Runtime / Code fields from tasks.md)
- **`N.X RED`** → write failing test; confirm failure
- **`N.X GREEN`** → minimal impl to pass
- **`N.X MOCK / VISUAL DIFF`** → UI sandwich for view components
- **`N.E EVAL`** → spawn haiku evaluator subagent; it runs code review + tests + spec scoring (Spec×0.4 + Runtime×0.4 + Code×0.2); ≥ threshold → PASS; < threshold → appends FIX tasks + retries (max 3 attempts; plateau < 5pt → escalate to user)
- **`N.X FIX`** → execute fix, re-fire EVAL

Final group has no CONTRACT/EVAL — uses `superpowers:verification-before-completion` instead.

Marks `- [x]` per-task immediately, not in batch.

## Phase 4: `/opsx:archive`

Runs `openspec archive` then post-archive cleanup:

1. Fill capability spec `## Purpose` (the TBD placeholder is what this fixes)
2. Update `openspec/specs/README.md` capability entry
3. Append to `CLAUDE.md` pitfalls if a new gotcha surfaced
4. Conditionally update project root `README.md` (user-visible changes only)

Cleanup step 3 now reads `eval-log.md` from archive — groups where `attempt > 1` are pitfall candidates for CLAUDE.md.

Plus dev log check (`docs/log/<today>.md`) and a single cleanup commit.

## Where rules live (architecture)

| Concern | Lives in | Why |
|---|---|---|
| Artifact paths and dependencies | Schema (`schema.yaml`) | Static graph — schema is the right tool |
| Per-artifact prompt rules (TDD pattern, CONTRACT/EVAL gates, MOCK/VISUAL DIFF sandwich) | Schema (per-artifact `instruction:`) + tasks template | Inheritable; survives forks |
| Project context (tech stack, file paths, conventions) | `openspec/config.yaml` | Project-specific, not workflow-specific |
| Phase orchestration (Status: gate, Visual Companion, archive cleanup) | Slash commands | Actions, not artifacts |
| Skill invocation timing (when to call TDD / review / verification) | `.claude/commands/opsx/apply.md` | Execution-time decisions |

## Known limitations

- **`openspec status` shows `requirements` and `mocks` as `ready` even when the files exist.** OpenSpec 1.2.0 does not substitute `{{date}}` / `{{change}}` template variables in `generates:` paths, so it can't locate the files to confirm they exist. The slash commands (`/opsx:explore` and `/opsx:propose`) perform the substitution and write the files at the resolved paths. This is expected — do not interpret `ready` as "missing"; verify by `ls docs/superpowers/specs/*-<topic>-requirements.md` instead.

## Migration history

- 2026-05-10: schema forked from `spec-driven`; `requirements` + `mocks` artifacts added; rules migrated from `openspec/config.yaml` to schema instructions; 4 slash commands rewritten. First validation target: `nas-https`.
- 2026-05-11: workflow extracted to `opsx-superpowers` plugin. Project-specific content moves to `openspec/config.yaml project:` section. Schema promoted to user-level via `opsx-install`. python-agent deletes project-level schema copy.
- 2026-05-xx: CONTRACT/EVAL harness added. `propose.md` generates `### Contract` blocks + pre-creates `contracts/` dir + `eval-log.md`. `apply.md` dispatches `N.0 CONTRACT` / `N.E EVAL` / `N.X FIX` task types; spawns haiku evaluator subagent per group. `archive.md` surfaces `eval-log.md` retry groups as CLAUDE.md pitfall candidates. `tasks.md` template updated to CONTRACT/EVAL structure.
- 2026-05-26: `multi-user-auth-admin-ui` archived. First full CONTRACT/EVAL harness run.
- `chat-file-pinning` still in-flight on pre-harness `tasks.md` — when archived, eval-log and contracts dirs won't exist; skip EVAL dispatch for that change only.
