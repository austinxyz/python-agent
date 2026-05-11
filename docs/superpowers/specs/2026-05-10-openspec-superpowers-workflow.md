# OpenSpec + Superpowers Workflow

**Status:** Active (as of 2026-05-10)
**Schema:** `superpowers-driven` at `openspec/schemas/superpowers-driven/`
**Slash commands:** `.claude/commands/opsx/{explore,propose,apply,archive}.md`

## TL;DR

Every change in this repo goes through 4 phases:

```
/opsx:explore <topic>   → docs/superpowers/specs/<date>-<topic>-requirements.md
       (5 phases: free-think → draft → review → UI mocks → commit)

/opsx:propose <topic>   → openspec/changes/<topic>/{proposal,specs,design,tasks}.md
       (Status: REVIEWED gate; --schema superpowers-driven)

/opsx:apply <topic>     → executes tasks.md with TDD + review skills wired in
       (each task group ends with code-review; final group runs verification)

/opsx:archive <topic>   → openspec/changes/archive/<date>-<topic>/ + 4 cleanups
       (capability ## Purpose; specs README; CLAUDE.md; project README; dev log)
```

## Why this exists

The `multi-user-auth-core` change exercised every step end-to-end on 2026-05-10. It exposed gaps: deferred code reviews almost shipped, the auto-generated capability spec had `## Purpose: TBD`, mocks lived by convention not by enforcement, and the agent had to re-discover the workflow rules in 4 different files. This schema + the 4 rewritten slash commands lock the workflow down so future changes can't drop these steps.

## Where to read more

- **Design doc** (the why and the architecture): `docs/superpowers/specs/2026-05-10-openspec-superpowers-workflow-design.md`
- **Implementation plan** (this rollout): `docs/superpowers/plans/2026-05-10-openspec-superpowers-workflow.md`
- **Schema definition**: `openspec/schemas/superpowers-driven/schema.yaml`
- **Per-phase command definitions**: `.claude/commands/opsx/<phase>.md`
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

Reads context (proposal, specs, design, mocks, requirements). Invokes `superpowers:test-driven-development` at session start. Walks tasks; dispatches by keyword in the task description (RED / GREEN / MOCK / VISUAL DIFF / Run superpowers:requesting-code-review). Final group invokes `superpowers:verification-before-completion`.

Marks `- [x]` per-task immediately, not in batch.

## Phase 4: `/opsx:archive`

Runs `openspec archive` then post-archive cleanup:

1. Fill capability spec `## Purpose` (the TBD placeholder is what this fixes)
2. Update `openspec/specs/README.md` capability entry
3. Append to `CLAUDE.md` pitfalls if a new gotcha surfaced
4. Conditionally update project root `README.md` (user-visible changes only)

Plus dev log check (`docs/log/<today>.md`) and a single cleanup commit.

## Where rules live (architecture)

| Concern | Lives in | Why |
|---|---|---|
| Artifact paths and dependencies | Schema (`schema.yaml`) | Static graph — schema is the right tool |
| Per-artifact prompt rules (TDD pattern, review checkpoints, MOCK/VISUAL DIFF sandwich) | Schema (per-artifact `instruction:`) | Inheritable; survives forks |
| Project context (tech stack, file paths, conventions) | `openspec/config.yaml` | Project-specific, not workflow-specific |
| Phase orchestration (Status: gate, Visual Companion, archive cleanup) | Slash commands | Actions, not artifacts |
| Skill invocation timing (when to call TDD / review / verification) | `.claude/commands/opsx/apply.md` | Execution-time decisions |

## Known limitations

- **`openspec status` shows `requirements` and `mocks` as `ready` even when the files exist.** OpenSpec 1.2.0 does not substitute `{{date}}` / `{{change}}` template variables in `generates:` paths, so it can't locate the files to confirm they exist. The slash commands (`/opsx:explore` and `/opsx:propose`) perform the substitution and write the files at the resolved paths. This is expected — do not interpret `ready` as "missing"; verify by `ls docs/superpowers/specs/*-<topic>-requirements.md` instead.

## Migration history

- 2026-05-10: schema forked from `spec-driven`; `requirements` + `mocks` artifacts added; rules migrated from `openspec/config.yaml` to schema instructions; 4 slash commands rewritten. First validation target: `nas-https` (next change to use this workflow).
- In-flight `multi-user-auth-admin-ui` (created on `spec-driven`) keeps that schema until archived. Per-change schema is locked at change-creation time.
- In-flight `chat-file-pinning` was created before this schema was finalized; its `requirements` and `mocks` artifacts will permanently show `status: ready` (known limitation above). When you eventually `/opsx:archive` it, the pre-flight guard will warn about incomplete artifacts — confirm to proceed, and consider whether to retrofit its `tasks.md` with the workflow's RED/GREEN + review-checkpoint structure before `/opsx:apply`.
