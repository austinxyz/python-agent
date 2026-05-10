# OpenSpec + Superpowers Workflow Schema Design

**Date:** 2026-05-10
**Scope:** Codify the 4-phase OpenSpec change workflow (explore → propose → apply → archive) used in this repo into a custom OpenSpec schema (`superpowers-driven`) plus revised slash commands. Source for this design: the just-shipped `multi-user-auth-core` change, which exercised every step end-to-end and surfaced the gaps we now plug.
**Status:** Design only. Implementation will follow as an OpenSpec change (likely named `openspec-superpowers-workflow`).

---

## Why

The 4-phase flow already half-exists in this repo. `.claude/commands/opsx/{explore,propose,apply,archive}.md` are wired up, and `openspec/config.yaml`'s `context` block injects superpowers-skill rules into artifact generation. But the gluing is fragile: tribal knowledge sits in 4 different files, the explore phase has no canonical output location, mocks/visual-companion/awesome-design-md are not explicitly triggered, and `openspec archive` leaves a `## Purpose\nTBD` placeholder that the human has to remember to fill in.

Concrete pain points surfaced by `multi-user-auth-core`:
- Bootstrap admin URL was undocumented across the deploy steps; the developer had to read source to find it.
- The auto-generated capability spec (`openspec/specs/multi-user-auth/spec.md`) shipped with `## Purpose\nTBD - created by archiving change. Update Purpose after archive.` because the post-archive cleanup is not codified.
- The deferred code-review batch (8 tasks marked `deferred to end-of-session ship batch`) almost shipped without ever running because the discipline was a comment, not a step.
- Mocks were saved to `docs/superpowers/specs/mocks/` by a manual convention not enforced by the schema.

OpenSpec ships a real schema mechanism (`openspec schema fork|init|validate`) that is the right tool for the structural concerns. Slash commands are the right tool for the orchestration concerns (the things that aren't artifact templates). This design splits the work along that line.

## Goals

1. Every change directory under `openspec/changes/` produced by this workflow contains a deterministic set of 6 artifacts (5 markdown + 1 html), all locatable from the change name + date alone.
2. Phase 1 (explore) always produces a reviewed `requirements.md` with explicit `Status: REVIEWED` before phase 2 starts. `/opsx:propose` refuses to run on a `Status: DRAFT` requirement.
3. Phase 4 (archive) updates `openspec/specs/<capability>/spec.md`'s `Purpose`, `openspec/specs/README.md`'s capability list, and `CLAUDE.md`'s pitfall section in one atomic command.
4. The TDD discipline (RED → GREEN per task) and code-review checkpoint (per task group) are encoded in the `tasks.md` template so they survive the planning phase, then actually invoked by `/opsx:apply` so they survive the execution phase.
5. UI work goes through Visual Companion and `awesome-design-md` for style picking; the chosen style and the rendered HTML mock are referenced from the requirements doc.

## Non-Goals

- Generalizing this workflow for other projects. The schema may be portable; the slash commands hard-code paths under `docs/superpowers/specs/` and reference project-specific files (e.g., `CLAUDE.md`'s pitfall section). Portability is a separate concern.
- Replacing OpenSpec's built-in `spec-driven` schema. We fork it; the fork inherits OpenSpec upgrades.
- Migrating already-archived changes or in-flight `multi-user-auth-admin-ui` to the new schema.
- Adding `review-log` or `dev-log` as durable artifacts. `dev-log` is already a habit (`docs/log/<date>.md`); `review-log` is over-formalization right now (commit messages + dev log already capture review history).

## Architecture

Three layers, each with a clear responsibility:

```
openspec/schemas/superpowers-driven/         ── artifact graph + templates
  schema.yaml
  templates/{requirements,proposal,specs,design,mocks,tasks}.md
                       │
                       ▼
.claude/commands/opsx/{explore,propose,apply,archive}.md
                       │  ── orchestration: review passes,
                       │     Visual Companion, awesome-design-md,
                       │     archive-time README cleanup
                       ▼
openspec/config.yaml                          ── project context
                       │     (tech stack, paths, conventions)
                       ▼
docs/superpowers/specs/2026-05-10-openspec-superpowers-workflow.md
                              ── human overview that links the above
```

**Schema** decides *what files exist and how they depend*. **Slash commands** decide *what actions happen at each phase*. **`config.yaml`** stays unchanged in role — it's the project context injected into every artifact-generation prompt. **Workflow doc** is the entry-point overview for someone who's never seen this before.

### Why fork `spec-driven` instead of building from scratch

`openspec schema fork spec-driven superpowers-driven` gives the new schema the existing 4 artifacts (proposal / specs / design / tasks) as a base. We add `requirements` and `mocks`. When OpenSpec upgrades `spec-driven` (new fields, template tweaks), we can diff and pick up improvements rather than reinvent.

## Schema artifact graph

```
        requirements                          ← new (root, always required)
              │
              ▼
         proposal                             ← carries HAS_UI_SURFACE: yes|no in frontmatter
              │
              ▼
          specs
              │
        ┌─────┴─────┐
        ▼           ▼
     design       mocks                       ← new (always required;
        │           │                            stub for HAS_UI_SURFACE: no)
        └─────┬─────┘
              ▼
           tasks
```

| Artifact | File location | Depends on | Stub allowed |
|---|---|---|---|
| `requirements` | `docs/superpowers/specs/<date>-<change-name>-requirements.md` | (root) | No |
| `proposal` | `openspec/changes/<change-name>/proposal.md` | requirements | No |
| `specs` | `openspec/changes/<change-name>/specs/**/*.md` | proposal | No |
| `design` | `openspec/changes/<change-name>/design.md` | proposal, specs | No |
| `mocks` | `docs/superpowers/specs/mocks/<date>-<change-name>-mocks.html` | proposal, specs | Yes (if `HAS_UI_SURFACE: no`) |
| `tasks` | `openspec/changes/<change-name>/tasks.md` | design, mocks | No |

`<date>` is `YYYY-MM-DD`, the date the requirements doc was first written. `<change-name>` is kebab-case, identical to the OpenSpec change directory name.

### Conditional `mocks` via stub instead of optional artifact

OpenSpec schema dependency graphs are static. Rather than expressing "mocks required only for UI changes" as a conditional dependency, mocks is **always required**. For backend-only changes the file is a 1-line stub:

```html
<!-- HAS_UI_SURFACE: no -->
This change has no UI surface; no visual mocks needed.
```

The `proposal` template carries a `HAS_UI_SURFACE: yes|no` frontmatter field. `/opsx:propose` reads it and either drives Visual Companion to produce a substantive mock or writes the stub directly.

### Per-artifact instruction block highlights

Each artifact's `instruction` field in `schema.yaml` injects rules at generation time. Notable rules:

- **`requirements`:** WHAT and WHY only, no implementation. Required sections: Goals / Non-Goals / Constraints / Success Criteria / User Stories / Open Questions. Reference relevant `openspec/specs/<capability>/spec.md` SHALL clauses. Frontmatter `Status:` field starts at `DRAFT`, flips to `REVIEWED` after the brainstorming review pass.
- **`proposal`:** Frontmatter MUST include `HAS_UI_SURFACE: yes|no` — drives whether mocks is substantive. Sections: Why / What Changes / New Capabilities / Modified Capabilities / Impact / Out of Scope.
- **`mocks`:** Self-contained HTML, no server dependency. References the design system (`docs/design/<style>.md`) selected via `awesome-design-md`. One `<section>` per UI flow + mobile equivalent. For backend-only changes: 1-line stub.
- **`tasks`:** Carries the existing `config.yaml` rules (each group ends with `superpowers:requesting-code-review` checkpoint; view-touching tasks have MOCK + VISUAL DIFF sandwich; final group runs `superpowers:verification-before-completion`). Every functional task pair is `RED` → `GREEN` (test before implementation).

## Slash command behavior

### `/opsx:explore <topic>`

5-phase command. Single user invocation, agent walks through phases in order.

**Phase 1 — Explore stance** (existing `.claude/commands/opsx/explore.md` body):
- Curious / patient / one question at a time, ASCII diagrams welcome
- Read project files, find integration points, surface hidden complexity
- No code, no implementation — thinking only
- No obligation to produce an artifact yet

**Phase 2 — Draft requirements**:
- When the agent judges the conversation has reached enough clarity, it writes `docs/superpowers/specs/<date>-<topic>-requirements.md` with frontmatter `Status: DRAFT`
- Structure follows the schema's `requirements` template, but contents are the agent's best capture of the conversation — rough is fine, TODOs allowed at this point

**Phase 3 — Brainstorming review** (invokes `superpowers:brainstorming`):
- Reads the draft and runs the brainstorming skill's spec self-review checklist:
  - Placeholder scan (no TBD / TODO / "..." remaining)
  - Internal consistency (no contradictions between sections)
  - Scope check (single change or needs decomposition)
  - Ambiguity check (each requirement has exactly one reading)
- Discovered gaps go back into the conversation as clarifying questions
- After all gaps are addressed, frontmatter flips to `Status: REVIEWED`

**Phase 4 — UI side-trip** (only when `HAS_UI_SURFACE: yes`):
- Invoke `awesome-design-md` skill — user picks a style (e.g., Notion, Linear, iOS Liquid Glass); the chosen style ID is appended to the requirements doc
- Invoke `superpowers:brainstorming`'s Visual Companion — render mocks in the browser, iterate with the user
- Save the final HTML to `docs/superpowers/specs/mocks/<date>-<topic>-mocks.html`

**Phase 5 — Commit + handoff**:
- Commit `requirements.md` (and `mocks.html` if produced)
- Output: "Requirements ready. Next: `/opsx:propose <topic>`."
- Do NOT auto-invoke propose

**Anti-pattern guard:** If the user says "just go ahead and propose / implement", the command refuses and instructs them to invoke `/opsx:propose` separately. Phase boundaries are explicit.

### `/opsx:propose <topic>`

**Pre-conditions:**
- `docs/superpowers/specs/<date>-<topic>-requirements.md` exists
- That file's frontmatter is `Status: REVIEWED` (not `DRAFT`)
- If either fails: refuse, point to `/opsx:explore`

**Steps:**
1. `openspec new change <topic> --schema superpowers-driven`
2. Generate proposal → specs → design → mocks → tasks in dependency order via `openspec instructions <artifact> --change <topic>`
3. After proposal generation, read its frontmatter:
   - `HAS_UI_SURFACE: yes` and Phase 4 of explore produced a real mocks file → confirm the file exists and is referenced from the proposal
   - `HAS_UI_SURFACE: no` → write 1-line stub at the locked mocks path
4. `tasks.md` is generated with the schema template's TDD + review structure baked in (RED/GREEN pairs, code-review checkpoints per group, MOCK/VISUAL DIFF sandwich for view tasks, verification-before-completion in the final group)
5. Output: "Change proposed. Next: `/opsx:apply <topic>`."

### `/opsx:apply <topic>`

**Job:** Execute `tasks.md`, actually invoking the superpowers skills the planning phase scaffolded in.

1. Session start: invoke `superpowers:test-driven-development`. The skill enforces "no GREEN without a RED predecessor" throughout the session.
2. Walk task groups in order:
   - `RED` task → write the test, run it, confirm it fails for the expected reason
   - `GREEN` task → implement minimal code, run the test, confirm it passes
   - `MOCK` task → open the corresponding section of `docs/superpowers/specs/mocks/<date>-<topic>-mocks.html` for visual reference
   - `VISUAL DIFF` task → bring up dev stack, navigate to the route, eyeball against the mock, fix token/text drift
   - Group-final `superpowers:requesting-code-review` task → invoke the skill on the group's diff; address CRITICAL/HIGH inline, MEDIUM/LOW in a follow-up note
3. Final group: invoke `superpowers:verification-before-completion`. Runs pytest / vitest / e2e / `console.log` audit / spec-vs-implementation diff.
4. Output: "Apply complete. Next: ship + `/opsx:archive <topic>`."

### `/opsx:archive <topic>`

**Job:** OpenSpec archive + the 4 cleanups that the bare CLI doesn't do.

1. `openspec archive <topic>` — moves the change directory to `openspec/changes/archive/<date>-<topic>/`, merges specs into `openspec/specs/<capability>/spec.md`.
2. **Fill `## Purpose` of the new/updated capability spec(s):** `openspec archive` leaves a `TBD` placeholder. Replace it with a 1-3 sentence summary derived from the proposal's "Why" + the requirements doc's Goals.
3. **Update `openspec/specs/README.md`:** add or update the capability's entry. Use the existing format (User Story / Coverage / Backend / Frontend / Acceptance criteria).
4. **Update `CLAUDE.md`'s pitfall section:** if the change surfaced any non-obvious gotcha (timing-sensitive bootstrap, env-var ordering, schema migration foot-gun, etc.), append a 2-3 line entry. Skip for changes that surfaced nothing new.
5. **Conditionally update project root `README.md`:** only if the change introduces user-visible new features or behavior changes. Operations changes (image build, NAS deploy) do NOT update the README.
6. **Dev log check:** verify `docs/log/<date>.md` has an entry for today; if not, prompt the user to write one (does not write on user's behalf — content is judgment-heavy).
7. Output: "Change archived. Workflow complete."

## Migration

**In-flight `multi-user-auth-admin-ui`:** keep on `spec-driven`. The schema is locked at change-creation time via `.openspec.yaml` inside the change directory. We do not retroactively migrate.

**Archived changes:** untouched — they're frozen and have no schema-dependent behavior.

**`openspec/config.yaml` rules cleanup:** the `context` block currently mixes project context with workflow rules. Migration:
- Project context (tech stack / paths / Qdrant rules / SSE conventions) → stays in `config.yaml`
- Workflow rules (per-group code-review checkpoint, MOCK/VISUAL DIFF sandwich, verification-before-completion task) → move to `schema.yaml`'s per-artifact `instruction` blocks
- Stale references (e.g., "Reference requirement IDs from docs/superpowers/specs/2026-05-05-requirements.md") → delete; each new change references its own requirements file

## Validation: first real change on `superpowers-driven`

Recommended first user: **`nas-https`** (Caddy/Traefik reverse proxy + Let's Encrypt for the NAS deploy). Reasons:
- Medium-sized — neither trivial like `auth-rate-limiting` nor sprawling like `multi-user-auth-core`
- Has both backend changes (`docker-compose.prod.yml`, env vars) and a small UI surface (status indicator showing cert expiry, possibly a manual-renewal button) — exercises the `HAS_UI_SURFACE: yes` branch and the awesome-design-md / Visual Companion path
- Security-sensitive — exercises the security-review path during apply
- Unblocks `cloud-deploy` and lets us flip `SESSION_COOKIE_SECURE=true`, validating the multi-user-auth design's deferred work

If `nas-https` reveals workflow gaps, the fix-up goes back into the schema or the slash commands; this design treats the first run as the integration test.

## Roll-out order (single PR target)

1. Fork the schema: `openspec schema fork spec-driven superpowers-driven`
2. Edit `schema.yaml` to add `requirements` + `mocks` artifacts and adjust dependencies
3. Edit `templates/{requirements,proposal,mocks,tasks}.md` to carry the rules currently in `config.yaml`
4. `openspec schema validate superpowers-driven`
5. Switch default in `openspec/config.yaml`: `schema: superpowers-driven`; prune migrated rules
6. Rewrite the four `.claude/commands/opsx/*.md` files per Section 3
7. Write `docs/superpowers/specs/2026-05-10-openspec-superpowers-workflow.md` (human overview, links into the schema and commands)
8. Commit, push, **do not yet archive this change as itself** — we're mid-brainstorm, the workflow we're designing is its own first user when we apply it to `nas-https`

## Open questions

None blocking. Soft items for follow-up:

1. **Q-01:** Should `awesome-design-md` style choice cascade as a project-level default (sticky) or be re-asked for every change? Current assumption: re-asked, but designs may converge on one style and it gets annoying. Revisit after 2-3 UI changes.
2. **Q-02:** Should the `mocks` stub for backend-only changes be its own artifact, or should the schema be smart enough to skip it? Current: stub. Revisit if OpenSpec adds conditional artifacts in a future release.
3. **Q-03:** When `nas-https` lands and the project gets HTTPS, should `SESSION_COOKIE_SECURE=true` migration be tracked as part of `nas-https` or split into a separate cleanup change? Tracked as part of `nas-https` for now.

## Risks / Trade-offs

- **R-01 — Schema drift from upstream `spec-driven`:** if OpenSpec evolves `spec-driven`'s artifact set, our fork stagnates. Mitigation: include a quarterly check that diffs `superpowers-driven` against current `spec-driven` and merges new fields/templates.
- **R-02 — Slash command divergence from schema:** the commands embed the phase logic; if someone updates the schema without updating the commands (or vice versa), the workflow breaks subtly. Mitigation: the workflow doc cross-links both; any PR touching one must reference the other.
- **R-03 — Phase boundaries too rigid for small changes:** running 5 phases of explore for a 10-line bug fix is overkill. Mitigation: this workflow is for *changes proposed via OpenSpec*. Tiny bug fixes go through normal commit flow without OpenSpec at all. The boundary "is it big enough to warrant OpenSpec" remains human judgment.
- **R-04 — `Status: REVIEWED` gate is bypassable:** an agent could flip `DRAFT` → `REVIEWED` without actually running the review pass. Mitigation: the brainstorming review pass is enforced by `/opsx:explore`'s phase 3, not by file inspection alone. Trust + observation, not cryptographic gating.
