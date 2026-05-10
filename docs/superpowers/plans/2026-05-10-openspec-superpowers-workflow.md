# OpenSpec + Superpowers Workflow Schema Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Codify this repo's 4-phase OpenSpec change workflow into a custom `superpowers-driven` schema plus 4 rewritten slash commands so future changes go through a deterministic explore→propose→apply→archive pipeline with TDD discipline, code-review checkpoints, and post-archive cleanup baked in.

**Architecture:** Fork OpenSpec's `spec-driven` schema → add `requirements` + `mocks` artifacts → migrate the workflow rules currently scattered in `openspec/config.yaml` and 4 slash command files into the schema templates + per-artifact instructions → rewrite the 4 slash commands to handle orchestration (Status:REVIEWED gate, Visual Companion + awesome-design-md, archive-time README cleanup) the schema doesn't cover.

**Tech Stack:** OpenSpec CLI (`@fission-ai/openspec`, `openspec schema` subcommands experimental but supported), YAML, Markdown, HTML.

**Spec source:** `docs/superpowers/specs/2026-05-10-openspec-superpowers-workflow-design.md`

---

## Known Unknown — Resolve in Task 1

OpenSpec's `spec-driven` schema declares `generates:` as paths relative to the change directory (`openspec/changes/<name>/`). The spec calls for two artifacts (`requirements`, `mocks`) to live OUTSIDE the change dir at `docs/superpowers/specs/`. We don't yet know if OpenSpec supports `generates:` pointing outside the change dir (e.g., `../../docs/superpowers/specs/...` or absolute paths).

Task 1's validation step probes this. Two branches:

- **Branch P (Path-supported):** schemas accept relative-up paths → keep design as-is, mocks/requirements live at `docs/superpowers/specs/`
- **Branch C (Convention-driven):** schemas reject paths outside change dir → drop `requirements` + `mocks` from the schema artifact list; the slash commands write to `docs/superpowers/specs/` directly via raw file I/O; the schema's `proposal` instruction enforces existence checks. Slash commands become single source of truth for these path conventions.

The plan as written below assumes **Branch P**. If Task 1 reveals **Branch C**, follow the contingency notes inline at Tasks 2, 3, 6, 8, 9.

---

## Task 1: Fork the schema and probe path-resolution behavior

**Files:**
- Create: `openspec/schemas/superpowers-driven/schema.yaml`
- Create: `openspec/schemas/superpowers-driven/templates/{proposal,spec,design,tasks}.md`

- [ ] **Step 1: Fork `spec-driven`**

```bash
openspec schema fork spec-driven superpowers-driven
```

Expected: creates `openspec/schemas/superpowers-driven/` with `schema.yaml` and `templates/` subdir. Output mentions "experimental" warning.

- [ ] **Step 2: Verify the fork copied cleanly**

```bash
openspec schema which superpowers-driven
ls openspec/schemas/superpowers-driven/templates/
openspec schema validate superpowers-driven
```

Expected:
- `which` shows `Source: project` and `Path: <repo>/openspec/schemas/superpowers-driven`
- `templates/` lists `proposal.md`, `spec.md`, `design.md`, `tasks.md`
- `validate` exits 0 with no errors

- [ ] **Step 3: Probe out-of-change-dir paths**

Edit `openspec/schemas/superpowers-driven/schema.yaml` and add ONE probe artifact at the end of the `artifacts:` list:

```yaml
  - id: probe
    generates: "../../../docs/superpowers/specs/probe-{{change}}.md"
    description: Probe — tests if schemas support out-of-change-dir paths
    template: probe.md
    instruction: |
      Probe artifact for testing path resolution. Delete after verification.
    requires: []
```

Create `openspec/schemas/superpowers-driven/templates/probe.md` with one line: `# Probe`.

Run validation:

```bash
openspec schema validate superpowers-driven
```

- [ ] **Step 4: Decide branch based on validation result**

If validate exits 0 → **Branch P confirmed**. Out-of-change-dir paths work. Remove the probe artifact + template:

```bash
# Edit schema.yaml: remove the probe artifact entry
rm openspec/schemas/superpowers-driven/templates/probe.md
openspec schema validate superpowers-driven
```

If validate fails with a path-resolution error → **Branch C confirmed**. The error message should mention path traversal or invalid generates path. Remove the probe and follow the Branch C contingencies at Tasks 2, 3, 6, 8, 9. Document the result in the commit message.

- [ ] **Step 5: Commit**

```bash
git add openspec/schemas/superpowers-driven/
git commit -m "chore: fork spec-driven schema as superpowers-driven baseline

Branch decision (Branch P or Branch C, document which): <result>"
```

---

## Task 2: Add `requirements` artifact to the schema

**Files:**
- Modify: `openspec/schemas/superpowers-driven/schema.yaml`
- Create: `openspec/schemas/superpowers-driven/templates/requirements.md`

> **Branch C contingency:** if Task 1 revealed Branch C, SKIP this task. Instead, document in `slash-commands` (Task 7) that `/opsx:explore` writes to `docs/superpowers/specs/<date>-<topic>-requirements.md` via raw file I/O, and the `proposal` instruction (modified in Task 4) enforces existence.

- [ ] **Step 1: Insert `requirements` artifact into `schema.yaml`**

Edit `openspec/schemas/superpowers-driven/schema.yaml`. Insert the new artifact as the FIRST entry under `artifacts:` (root, no requires):

```yaml
  - id: requirements
    generates: "../../../docs/superpowers/specs/{{date}}-{{change}}-requirements.md"
    description: Reviewed requirements doc — output of /opsx:explore
    template: requirements.md
    instruction: |
      Capture WHAT and WHY before any implementation thinking.

      Required frontmatter:
      - Date (YYYY-MM-DD, the date this file was first written)
      - Change name (kebab-case, matches openspec change directory name)
      - Status: DRAFT or REVIEWED
      - HAS_UI_SURFACE: yes or no

      Required sections (in order):
      - Goals: what this change achieves
      - Non-Goals: what is explicitly out of scope
      - Constraints: hard limits (perf, security, deploy targets, etc.)
      - Success Criteria: how we know we're done
      - User Stories: who uses this and how
      - Open Questions: unresolved decisions

      Reference any relevant SHALL clauses from openspec/specs/<capability>/spec.md.

      Status flow: DRAFT (after first write) → REVIEWED (after brainstorming
      review pass catches placeholders, contradictions, scope creep, ambiguity).
      /opsx:propose REJECTS files with Status: DRAFT.

      No implementation details. No code. This is a requirements doc.
    requires: []
```

Then update the `proposal` artifact's `requires:` list to add `requirements`:

```yaml
  - id: proposal
    # ...existing fields...
    requires:
      - requirements
```

- [ ] **Step 2: Create `templates/requirements.md`**

Write to `openspec/schemas/superpowers-driven/templates/requirements.md`:

```markdown
---
Date: {{date}}
Change: {{change}}
Status: DRAFT
HAS_UI_SURFACE: <yes|no>
---

# {{change}} Requirements

## Goals

<What this change achieves. Bullet list, 3-7 items.>

## Non-Goals

<What is explicitly out of scope. Bullet list. Important to prevent scope creep.>

## Constraints

<Hard limits: performance, security, deployment targets, dependencies, compatibility windows.>

## Success Criteria

<Measurable outcomes that prove the change is done. Should be testable.>

## User Stories

<Who uses this and how. Format: "As a <role>, I want <goal> so that <benefit>."
For internal/ops changes use developer/operator/admin as the role.>

## Open Questions

<Unresolved decisions. Each should be answered before Status: REVIEWED.
Format: "Q-NN: <question>" with optional context.>

## Referenced Capabilities

<List openspec/specs/<capability>/spec.md SHALL clauses this change touches.
Use "ADD <capability>" for new capabilities, "MODIFY <capability>" for existing.>
```

- [ ] **Step 3: Validate the schema**

```bash
openspec schema validate superpowers-driven
```

Expected: exits 0. If fails on the `requirements` artifact, fix the YAML or template syntax.

- [ ] **Step 4: Commit**

```bash
git add openspec/schemas/superpowers-driven/schema.yaml openspec/schemas/superpowers-driven/templates/requirements.md
git commit -m "feat(schema): add requirements artifact to superpowers-driven

Root artifact (no dependencies). Outputs to docs/superpowers/specs/.
Frontmatter: Status (DRAFT/REVIEWED) and HAS_UI_SURFACE (yes/no).
proposal artifact now requires requirements."
```

---

## Task 3: Add `mocks` artifact to the schema

**Files:**
- Modify: `openspec/schemas/superpowers-driven/schema.yaml`
- Create: `openspec/schemas/superpowers-driven/templates/mocks.html`

> **Branch C contingency:** if Task 1 revealed Branch C, SKIP this task. Slash commands handle the mocks file path convention.

- [ ] **Step 1: Insert `mocks` artifact into `schema.yaml`**

Add to `artifacts:` list AFTER `specs` and BEFORE `design`:

```yaml
  - id: mocks
    generates: "../../../docs/superpowers/specs/mocks/{{date}}-{{change}}-mocks.html"
    description: HTML mocks for UI changes; 1-line stub for backend-only changes
    template: mocks.html
    instruction: |
      Self-contained HTML — open in browser, no server needed.

      Read proposal.md frontmatter HAS_UI_SURFACE field:
      - HAS_UI_SURFACE: yes → produce real mocks (one <section> per UI flow,
        plus mobile equivalent). Reference design tokens from the design system
        chosen via awesome-design-md (e.g., docs/design/notion.md if Notion).
        Lock-down level is design tokens (e.g., bg-notion-brand-navy) and
        verbatim text strings, NOT pixel measurements.
      - HAS_UI_SURFACE: no → write the stub form (see template).

      File MUST be self-contained: inline <style>, no external CSS or JS.
      Do not embed images via http:// — use SVG or omit.
    requires:
      - proposal
      - specs
```

Then update the `tasks` artifact's `requires:` to add `mocks`:

```yaml
  - id: tasks
    # ...existing fields...
    requires:
      - specs
      - design
      - mocks
```

- [ ] **Step 2: Create `templates/mocks.html`**

Write to `openspec/schemas/superpowers-driven/templates/mocks.html`:

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>{{change}} mocks</title>
  <!-- HAS_UI_SURFACE: <yes|no> -->
  <style>
    /* Design tokens go here. Reference docs/design/<style>.md for values. */
    body { font-family: -apple-system, BlinkMacSystemFont, sans-serif; margin: 0; padding: 24px; }
    section { margin-bottom: 48px; }
    h1, h2 { margin-top: 0; }
    .stub { color: #888; font-style: italic; }
  </style>
</head>
<body>

<!--
  HAS_UI_SURFACE: no  → keep just this stub paragraph; delete the rest.
  HAS_UI_SURFACE: yes → delete this stub; add one <section> per UI flow.
-->
<section class="stub">
  <h1>{{change}}</h1>
  <p>This change has no UI surface; no visual mocks needed.</p>
</section>

<!-- Example real-mock section (delete or fill in):
<section id="example-flow">
  <h2>Example Flow Name</h2>
  <p>Description and intent. What problem does this UI solve?</p>
  <div class="mock">
    <!-- self-contained markup using design tokens -->
  </div>
</section>
-->

</body>
</html>
```

- [ ] **Step 3: Validate the schema**

```bash
openspec schema validate superpowers-driven
```

Expected: exits 0.

- [ ] **Step 4: Commit**

```bash
git add openspec/schemas/superpowers-driven/schema.yaml openspec/schemas/superpowers-driven/templates/mocks.html
git commit -m "feat(schema): add mocks artifact to superpowers-driven

Always required; backend-only changes use a 1-line stub form.
Outputs to docs/superpowers/specs/mocks/. tasks artifact now requires mocks."
```

---

## Task 4: Update `proposal` template — add HAS_UI_SURFACE frontmatter

**Files:**
- Modify: `openspec/schemas/superpowers-driven/templates/proposal.md`
- Modify: `openspec/schemas/superpowers-driven/schema.yaml` (proposal `instruction` block)

- [ ] **Step 1: Read the current proposal template**

```bash
cat openspec/schemas/superpowers-driven/templates/proposal.md
```

The forked template should match the `spec-driven` proposal template. Note its current structure.

- [ ] **Step 2: Rewrite `templates/proposal.md` with frontmatter**

Replace the file with:

```markdown
---
Date: {{date}}
Change: {{change}}
HAS_UI_SURFACE: <yes|no>
Requirements: docs/superpowers/specs/{{date}}-{{change}}-requirements.md
---

## Why

<1-2 sentences on the problem or opportunity. Why now?>

## What Changes

<Bullet list of changes. Be specific about new capabilities, modifications,
or removals. Mark breaking changes with **BREAKING**.>

## Capabilities

### New Capabilities

<List capabilities being introduced. Each becomes a new specs/<name>/spec.md.
Use kebab-case names. Empty if no new capabilities.>

### Modified Capabilities

<List existing capabilities whose REQUIREMENTS change (not just implementation).
Each needs a delta spec at specs/<capability>/spec.md. Check openspec/specs/
for existing names. Empty if no requirement changes.>

## Impact

<Affected code, APIs, dependencies, or systems. Bullet list of file groups.>

## Out of Scope

<Explicitly excluded. Reference future change names if known
(e.g., "deferred to future-change-name").>
```

- [ ] **Step 3: Update the `proposal` artifact's `instruction:` in `schema.yaml`**

Replace the `instruction` block of the `proposal` artifact with:

```yaml
    instruction: |
      Build on requirements.md (already produced by /opsx:explore).

      Required frontmatter:
      - Date (matches requirements.md date)
      - Change (kebab-case, matches change directory name)
      - HAS_UI_SURFACE: yes or no — drives whether mocks artifact is real or stub
      - Requirements: path to the requirements doc

      Required sections (in order):
      - Why: 1-2 sentences on problem/opportunity. Why now?
      - What Changes: bullet list of changes. Mark breaking changes with **BREAKING**.
      - Capabilities:
        - New Capabilities: kebab-case names becoming new specs/<name>/spec.md
        - Modified Capabilities: existing capability folders getting delta specs
      - Impact: affected code, APIs, dependencies, file groups
      - Out of Scope: explicitly excluded; reference future change names

      The Capabilities section creates the contract for the specs phase.
      Research existing openspec/specs/ before writing it.

      Keep concise (1-2 pages). Why, not how. Implementation belongs in design.md.
    requires:
      - requirements
```

- [ ] **Step 4: Validate**

```bash
openspec schema validate superpowers-driven
```

Expected: exits 0.

- [ ] **Step 5: Commit**

```bash
git add openspec/schemas/superpowers-driven/
git commit -m "feat(schema): add HAS_UI_SURFACE frontmatter to proposal template

Drives mocks artifact branching (real mocks vs stub).
proposal references requirements doc by path in frontmatter."
```

---

## Task 5: Update `tasks` template — encode TDD + review structure

**Files:**
- Modify: `openspec/schemas/superpowers-driven/templates/tasks.md`
- Modify: `openspec/schemas/superpowers-driven/schema.yaml` (tasks `instruction` block)

- [ ] **Step 1: Rewrite `templates/tasks.md`**

Replace with a richer template that demonstrates the TDD + review structure:

```markdown
## 1. <!-- First task group: setup or scaffold -->

- [ ] 1.1 RED — <!-- failing test for first behavior -->
- [ ] 1.2 GREEN — <!-- minimal implementation to pass 1.1 -->
- [ ] 1.3 RED — <!-- next failing test -->
- [ ] 1.4 GREEN — <!-- minimal impl -->
- [ ] 1.Z Run superpowers:requesting-code-review on the diff for group 1; address CRITICAL/HIGH findings before moving on

## 2. <!-- Next task group: feature work -->

<!-- For frontend tasks that touch a VIEW / MODAL / named LAYOUT (>50 lines):
     sandwich the GREEN with MOCK + VISUAL DIFF tasks. Example: -->

- [ ] 2.1 MOCK — open docs/superpowers/specs/mocks/{{date}}-{{change}}-mocks.html#<anchor>; note Notion tokens used (bg-notion-*, text-notion-*) and verbatim text strings
- [ ] 2.2 RED — <!-- vitest case asserting wrapper.classes() includes the tokens -->
- [ ] 2.3 GREEN — <!-- implement the view -->
- [ ] 2.4 VISUAL DIFF — bring up dev stack (npm run dev:up); navigate to the route; eyeball rendered UI against the mock; fix any token/color/text drift
- [ ] 2.Z Run superpowers:requesting-code-review on the diff for group 2

## 3. <!-- Verification + ship -->

- [ ] 3.1 Run full pytest suite — ensure no regressions
- [ ] 3.2 Run full vitest suite — ensure no regressions
- [ ] 3.3 Run Playwright e2e suite (if applicable)
- [ ] 3.4 Run superpowers:verification-before-completion (cd backend && pytest; cd frontend && npm test; grep -r console.log frontend/src; diff review)
- [ ] 3.5 Final superpowers:requesting-code-review on the entire change diff
```

- [ ] **Step 2: Update the `tasks` artifact's `instruction:` in `schema.yaml`**

Replace the `tasks` artifact's `instruction:` block with:

```yaml
    instruction: |
      Create the task list that breaks down the implementation work.

      **STRUCTURAL RULES (apply phase parses checkboxes):**
      - Tasks MUST be: `- [ ] N.X <description>`
      - Group related tasks under `## N. <group name>` headings
      - Order tasks by dependency

      **TDD discipline (mandatory):**
      - Each task introducing NEW behavior MUST be preceded by a failing-test task
      - Pattern: `- [ ] N.X RED — write failing pytest/vitest test for <behavior>`
        followed by `- [ ] N.X+1 GREEN — minimal impl to pass the test`
      - Bug fixes MUST be preceded by a regression test that reproduces the bug

      **Review checkpoints (mandatory):**
      - Each `## N` task group MUST end with:
        `- [ ] N.Z Run superpowers:requesting-code-review on the diff for group N; address CRITICAL/HIGH findings before moving on`
      - Final group MUST include:
        `- [ ] M.K Run superpowers:verification-before-completion`

      **Frontend view sandwich (when applicable):**
      For each frontend GREEN task implementing a VIEW / MODAL / named LAYOUT
      component (>50 lines; utility helpers / stores / interceptors are exempt),
      the GREEN task MUST be sandwiched:
      - Preceding: `- [ ] N.X MOCK — open docs/superpowers/specs/mocks/<file>.html#<anchor>; note tokens + verbatim strings`
      - Following: `- [ ] N.X+2 VISUAL DIFF — bring up dev stack; navigate; eyeball against mock; fix drift`

      **Token-locked tests (when applicable):**
      When a frontend RED test corresponds to a requirement that names design
      tokens, the test SHALL assert presence via wrapper.classes() — e.g.,
      `expect(cls).toMatch(/bg-notion-primary/)` — not only data-* selectors.
      This makes design tokens load-bearing in the test suite.

      **LangGraph rule:** graph tasks MUST test nodes independently (unit)
      before testing the full graph flow (integration).

      Skill names: when a task should invoke a superpowers skill, name it
      explicitly (e.g., `Invoke superpowers:test-driven-development to scaffold
      tests for the new LangGraph node`).
    requires:
      - specs
      - design
      - mocks
```

- [ ] **Step 3: Validate**

```bash
openspec schema validate superpowers-driven
```

Expected: exits 0.

- [ ] **Step 4: Commit**

```bash
git add openspec/schemas/superpowers-driven/
git commit -m "feat(schema): encode TDD + review structure in tasks template

Migrates the rules previously in openspec/config.yaml's tasks rules block:
- RED → GREEN pairs for new behavior
- Per-group code-review checkpoint
- MOCK + VISUAL DIFF sandwich for frontend views
- verification-before-completion in final group
- Token-locked tests via wrapper.classes()
- LangGraph node-then-graph testing"
```

---

## Task 6: Switch project to use new schema; clean migrated rules from config.yaml

**Files:**
- Modify: `openspec/config.yaml`

- [ ] **Step 1: Switch the default schema**

Edit `openspec/config.yaml` line 1:

```yaml
schema: superpowers-driven
```

- [ ] **Step 2: Remove migrated rules**

Delete the entire `tasks:` block under `rules:` in `openspec/config.yaml` (lines ~85-93 in the current file). These rules are now in the `tasks` artifact's `instruction` block in the schema.

Also delete the `proposal:` rule referencing the dated requirements file (since each change now has its own requirements file referenced via frontmatter):

> "Reference the requirement IDs from docs/superpowers/specs/2026-05-05-requirements.md (e.g., CHAT-04, ING-01) that this change addresses."

And delete the `proposal:` rule about mocks file location (now schema-enforced):

> "If the change adds a new view / modal / layout / sidebar item, proposal.md MUST link the corresponding mock file under docs/superpowers/specs/mocks/<date>-<topic>-mocks.html. If mocks do not yet exist, the proposal MUST require a brainstorming session with visual companion BEFORE implementation begins, or explicitly state 'no visual mocks; design emerges inline (last resort)'."

And delete the `design:` rule referencing the dated design doc:

> "Reference the brainstorming spec doc docs/superpowers/specs/2026-05-05-knowledge-agent-design.md as primary input when relevant."

- [ ] **Step 3: Verify what stays**

After editing, the `rules:` block in `openspec/config.yaml` should contain ONLY:
- `proposal:` rules about Non-Goals section, Capabilities section discipline, brainstorming-mockups note (kept)
- `design:` rules about decisions/alternatives, Qdrant filter, SSE format, UI Fidelity section (kept)
- `specs:` rule about Notion tokens in requirement text (kept)

The `tasks:` block under `rules:` should be empty or removed entirely.

- [ ] **Step 4: Smoke-test the new default**

```bash
# Create a throwaway change with the new default schema
openspec new change __schema-smoke-test
openspec status --change __schema-smoke-test --json
```

Expected: `schemaName: superpowers-driven`. The artifact list should show `requirements`, `proposal`, `specs`, `design`, `mocks`, `tasks` (Branch P) OR the original 4 with our updated instructions (Branch C).

```bash
# Clean up the smoke test
rm -rf openspec/changes/__schema-smoke-test
```

- [ ] **Step 5: Validate the schema once more from the project default**

```bash
openspec schema validate
```

Expected: exits 0 (no schema name needed since it's now the default).

- [ ] **Step 6: Commit**

```bash
git add openspec/config.yaml
git commit -m "chore: switch default schema to superpowers-driven; prune migrated rules

config.yaml now contains only project context (tech stack, paths, conventions)
and rules that don't fit naturally in artifact instructions (e.g., reference
to existing capability spec names). The tasks rules block migrated to the
schema's tasks artifact instruction in commit <previous-commit-sha>."
```

---

## Task 7: Rewrite `/opsx:explore` — 5-phase flow

**Files:**
- Modify: `.claude/commands/opsx/explore.md`

- [ ] **Step 1: Read the current explore.md**

```bash
cat .claude/commands/opsx/explore.md
```

The first ~80 lines preserve the explore stance (curious / patient / no implementation). Keep that block; we add Phase 2-5 below it.

- [ ] **Step 2: Replace the file**

Write to `.claude/commands/opsx/explore.md`:

```markdown
---
name: "OPSX: Explore"
description: "Explore mode + draft requirements — produces docs/superpowers/specs/<date>-<topic>-requirements.md"
category: Workflow
tags: [workflow, explore, experimental, thinking]
---

5-phase explore command. Single user invocation, agent walks through phases in order.

**Input**: The argument after `/opsx:explore` is whatever the user wants to think about. Could be a vague idea ("real-time collaboration"), a specific problem ("the auth system is getting unwieldy"), a comparison ("postgres vs sqlite for this"), or nothing (just enter explore mode).

If a topic is given, derive a kebab-case `<topic>` from it (e.g., "real-time collaboration" → `realtime-collab`). The same `<topic>` will be the OpenSpec change name in `/opsx:propose`.

---

## Phase 1 — Explore stance (free thinking)

**This phase is the existing explore mode. NEVER write code, never modify code, never propose implementation. Thinking only.**

You may:
- Read files, search code, investigate the codebase
- Map existing architecture relevant to the discussion
- Find integration points and identify patterns already in use
- Surface hidden complexity
- Use ASCII diagrams liberally when they help
- Ask clarifying questions one at a time
- Compare options conversationally

You may NOT:
- Write or modify code
- Create OpenSpec artifacts (proposal/design/specs/tasks)
- Tell the user "now I'll implement"

The goal of Phase 1 is **the user's brain becomes clear about what they want**.

---

## Phase 2 — Draft requirements (DRAFT status)

When you judge that the conversation has reached enough clarity (typically after 5-15 turns), proactively offer:

> "I think we have enough to write a draft requirements doc. I'll save it to `docs/superpowers/specs/<date>-<topic>-requirements.md` with `Status: DRAFT`. We'll review it together in the next phase."

Wait for the user's confirmation. Then write the file using the requirements template (`openspec instructions requirements --schema superpowers-driven --json` returns the template). Required frontmatter:

```yaml
---
Date: <YYYY-MM-DD>
Change: <topic>
Status: DRAFT
HAS_UI_SURFACE: <yes|no — your best guess from the conversation>
---
```

Sections (Goals / Non-Goals / Constraints / Success Criteria / User Stories / Open Questions / Referenced Capabilities). Rough is fine. TODOs are allowed at this stage.

> **Branch C (if Task 1 of the implementation plan revealed Branch C):** the schema does NOT declare `requirements` as an artifact. Write the file directly via Write tool to the same path. The path convention is enforced by THIS command (you), not by `openspec new change`.

`git add` the file but DO NOT commit yet. Phase 5 commits.

---

## Phase 3 — Brainstorming review (REVIEWED status)

Invoke `superpowers:brainstorming` with the draft as input. Run its spec self-review checklist:

1. **Placeholder scan:** Any TBD / TODO / "..." / "fill in" remaining? Fix or escalate to the user.
2. **Internal consistency:** Do sections contradict each other? Does the architecture in (implicit) thinking match the requirements?
3. **Scope check:** Is this focused enough for a single OpenSpec change, or does it need decomposition? If it needs splitting, propose 2-3 sub-changes and ask which to pursue first.
4. **Ambiguity check:** Could any requirement be interpreted two ways? Pick one with the user, make it explicit.

After all gaps are resolved, change frontmatter `Status: DRAFT` → `Status: REVIEWED`. The propose phase will refuse to start if it sees `DRAFT`.

---

## Phase 4 — UI side-trip (only if HAS_UI_SURFACE: yes)

Skip this phase entirely if `HAS_UI_SURFACE: no`.

If `yes`:

**Style selection** — invoke the `awesome-design-md` skill. The skill presents available design system options (Notion, Linear, iOS Liquid Glass, etc.). The user picks one. Append the chosen style ID to the requirements doc as the last line:

```markdown
## Design System

Selected via awesome-design-md: `<style-id>` (see docs/design/<style-id>.md).
```

**Visual mocking** — invoke `superpowers:brainstorming`'s Visual Companion. The companion renders mocks in the browser; iterate with the user until the layouts and tokens are nailed down. Save the final HTML to:

```
docs/superpowers/specs/mocks/<date>-<topic>-mocks.html
```

The HTML must be self-contained (inline CSS, no external assets). Reference the chosen design system's tokens.

> **Branch C (if applicable):** same path; the file is written directly via Write tool.

---

## Phase 5 — Commit + handoff

Commit the requirements (and mocks if produced):

```bash
git add docs/superpowers/specs/<date>-<topic>-requirements.md
# also if mocks produced:
git add docs/superpowers/specs/mocks/<date>-<topic>-mocks.html
git commit -m "docs: requirements for <topic>"
```

Output to the user:

> "Requirements ready and reviewed. Next: `/opsx:propose <topic>` (do not auto-invoke; let the user trigger it)."

**Anti-pattern guard:** if the user says "just go ahead and propose / implement", REFUSE. Tell them: "Phase boundaries are explicit. Run `/opsx:propose <topic>` separately so the propose phase has a clean entry."

---

## Stance reminders

- One question at a time
- Multiple choice preferred over open-ended when applicable
- Patient — don't rush phases. If Phase 1 needs 20 turns, that's fine
- Visualize freely (ASCII diagrams)
- Open threads, not interrogations — surface multiple directions, let the user follow what resonates

## What you might do (not exhaustive)

**Explore the problem space** — clarifying questions, challenge assumptions, reframe, find analogies.

**Investigate the codebase** — map existing architecture, find integration points, identify patterns already in use, surface hidden complexity.

**Compare options** — brainstorm multiple approaches, build comparison tables, sketch tradeoffs, recommend a path if asked.

**Visualize** — ASCII diagrams when text isn't sufficient.
```

- [ ] **Step 3: Verify the file structure**

```bash
grep -c '^## Phase' .claude/commands/opsx/explore.md
```

Expected: `5` (one heading per phase).

- [ ] **Step 4: Commit**

```bash
git add .claude/commands/opsx/explore.md
git commit -m "feat(opsx): rewrite explore.md as 5-phase flow

Phase 1 free-thinking → Phase 2 draft → Phase 3 brainstorming review →
Phase 4 (conditional) UI mocks → Phase 5 commit + handoff.
Status: DRAFT/REVIEWED gate enforced for /opsx:propose."
```

---

## Task 8: Rewrite `/opsx:propose` — Status:REVIEWED gate + schema flag

**Files:**
- Modify: `.claude/commands/opsx/propose.md`

- [ ] **Step 1: Replace propose.md with the new flow**

Write to `.claude/commands/opsx/propose.md`:

```markdown
---
name: "OPSX: Propose"
description: Create an OpenSpec change from a reviewed requirements doc; generates all artifacts
category: Workflow
tags: [workflow, artifacts, experimental]
---

Create an OpenSpec change with all artifacts. Pre-condition: a reviewed requirements doc exists at `docs/superpowers/specs/<date>-<topic>-requirements.md`.

**Input**: The argument after `/opsx:propose` is the change name (kebab-case). The same `<topic>` used in `/opsx:explore`.

---

**Steps**

### 1. Pre-flight: requirements gate

Locate the requirements doc:

```bash
ls docs/superpowers/specs/*-<topic>-requirements.md 2>/dev/null
```

If no file matches → REFUSE with:

> "No requirements doc found for `<topic>`. Run `/opsx:explore <topic>` first to produce `docs/superpowers/specs/<date>-<topic>-requirements.md`."

If found, read its frontmatter. Check `Status:` field:

- `Status: DRAFT` → REFUSE with:
  > "Requirements doc is `Status: DRAFT`. Run `/opsx:explore <topic>` Phase 3 (brainstorming review) to bring it to `Status: REVIEWED` before proposing."
- `Status: REVIEWED` → proceed.

Also note `HAS_UI_SURFACE` — drives mocks branching at step 4.

### 2. Create the change directory

```bash
openspec new change <topic> --schema superpowers-driven
```

This scaffolds `openspec/changes/<topic>/` with `.openspec.yaml` set to `superpowers-driven`.

### 3. Generate artifacts in dependency order

```bash
openspec status --change <topic> --json
```

Use the `artifacts` array to walk dependency-ready artifacts. For each:

```bash
openspec instructions <artifact-id> --change <topic> --json
```

Read the returned `template`, `instruction`, `dependencies`. For each dependency listed, READ the dependency artifact file from disk before generating.

Use the **TodoWrite tool** to track artifact-generation progress.

Order (Branch P): `proposal` → `specs` → `design` → `mocks` → `tasks`.
(`requirements` was created in `/opsx:explore`; openspec sees it as `done`.)

Order (Branch C, if applicable): `proposal` → `specs` → `design` → `tasks`. The mocks file at `docs/superpowers/specs/mocks/<date>-<topic>-mocks.html` is written by THIS command via Write tool, branching on HAS_UI_SURFACE: yes/no.

### 4. After proposal generation: branch on HAS_UI_SURFACE

Read the just-written `openspec/changes/<topic>/proposal.md` frontmatter.

- `HAS_UI_SURFACE: yes` → confirm `docs/superpowers/specs/mocks/<date>-<topic>-mocks.html` exists with substantive content (more than the stub form). If missing or stub-only, REFUSE and direct the user back to `/opsx:explore` Phase 4.
- `HAS_UI_SURFACE: no` → mocks file should be the 1-line stub. The schema's mocks instruction handles the stub generation; verify after that step.

### 5. Verify all artifacts

```bash
openspec status --change <topic>
```

Every artifact should be `done`. If any are not, troubleshoot the specific artifact.

### 6. Commit and handoff

```bash
git add openspec/changes/<topic>/ docs/superpowers/specs/mocks/*-<topic>-mocks.html
git commit -m "docs: propose <topic> change"
```

Output:

> "Change `<topic>` proposed. Artifacts: requirements (in docs/), proposal, specs, design, mocks, tasks. Next: `/opsx:apply <topic>`."

---

**Guardrails**

- NEVER bypass the Status: REVIEWED check. If the user insists, send them back to `/opsx:explore` Phase 3.
- NEVER write artifacts that the schema would generate via `openspec instructions`. Always go through the CLI.
- If a change with that name already exists at `openspec/changes/<topic>/`, ask the user whether to continue (delete and re-create) or pick a different name.
- `context` and `rules` from `openspec instructions` output are constraints on YOU (the agent), not content to copy into artifact files.
```

- [ ] **Step 2: Verify the file**

```bash
grep -c '^### [0-9]' .claude/commands/opsx/propose.md
```

Expected: `6` (six numbered steps).

- [ ] **Step 3: Commit**

```bash
git add .claude/commands/opsx/propose.md
git commit -m "feat(opsx): rewrite propose.md with Status:REVIEWED gate

Pre-flight requires docs/superpowers/specs/<date>-<topic>-requirements.md
with Status: REVIEWED. Branches on HAS_UI_SURFACE for mocks generation.
Always passes --schema superpowers-driven."
```

---

## Task 9: Rewrite `/opsx:apply` — explicit skill invocations at gates

**Files:**
- Modify: `.claude/commands/opsx/apply.md`

- [ ] **Step 1: Replace apply.md**

Write to `.claude/commands/opsx/apply.md`:

```markdown
---
name: "OPSX: Apply"
description: Execute tasks.md with TDD + review skills wired into the gates
category: Workflow
tags: [workflow, artifacts, experimental]
---

Execute the tasks defined in `openspec/changes/<topic>/tasks.md`. Invoke superpowers skills at the gates the planning phase wired in.

**Input**: Optionally specify a change name (e.g., `/opsx:apply add-auth`). If omitted, infer from conversation context. If ambiguous, run `openspec list --json` and use **AskUserQuestion** to let the user select.

---

**Steps**

### 1. Select change + read context

Announce: "Using change: `<name>`. Override: `/opsx:apply <other>`."

```bash
openspec status --change <name> --json
openspec instructions apply --change <name> --json
```

Parse `contextFiles` from the apply instructions. READ each one (proposal, specs, design, mocks, requirements) so you have full context before touching code.

### 2. Session start: invoke superpowers:test-driven-development

Use the **Skill** tool to invoke `superpowers:test-driven-development`. The skill enforces "no GREEN without a RED predecessor" throughout the session. This is mandatory; do not skip.

### 3. Walk task groups

For each `## N` task group in `tasks.md`:

For each task, dispatch by prefix:

- **`- [ ] N.X RED — ...`** → write the failing test, run it, confirm the failure mode matches the description (often "function not defined" or "expected X got undefined"). Mark the checkbox.

- **`- [ ] N.Y GREEN — ...`** → write the minimal code to pass. Run the test. Confirm pass. Mark the checkbox.

- **`- [ ] N.Z MOCK — ...`** → open the mock file at the path shown in the task. Note the design tokens and verbatim text strings called out. Mark the checkbox.

- **`- [ ] N.W VISUAL DIFF — ...`** → bring up the dev stack (`npm run dev:up` or whatever the task says), navigate to the route, eyeball the rendered UI against the mock. Fix any token/color/text drift. Mark the checkbox.

- **`- [ ] N.Z Run superpowers:requesting-code-review on the diff for group N`** → invoke `superpowers:requesting-code-review` via the **Skill** tool. Pass the group's diff as input. Address CRITICAL/HIGH findings inline before moving on; MEDIUM/LOW go to a follow-up note in the change directory.

- **Final group's verification task** (`Run superpowers:verification-before-completion`) → invoke `superpowers:verification-before-completion`. Runs pytest / vitest / e2e / `console.log` audit. Fix any failures before marking complete.

Mark each task `- [x]` immediately after completing it (not in a batch at the end).

### 4. On completion or pause: status

Run:

```bash
openspec status --change <name>
```

If all tasks are `- [x]`:

> "Apply complete. Suggest: ship + `/opsx:archive <name>`."

If paused (blocker, error, ambiguity, user interrupt):

> "Paused at task `<N.X>`. Reason: <description>. Options: <1>, <2>, <other approach>. What would you like to do?"

---

**Guardrails**

- DO invoke `superpowers:test-driven-development` at session start. Don't pretend.
- DO invoke `superpowers:requesting-code-review` at every group's `N.Z` checkpoint. Don't batch all reviews to the end.
- DO mark each task `- [x]` immediately after completing it.
- DON'T skip RED tasks ("the test is obvious; I'll just GREEN"). The TDD skill catches this.
- DON'T proceed past a group's checkpoint with unaddressed CRITICAL or HIGH review findings.
- DO pause if a task reveals a design issue. Suggest updating proposal/design/specs as appropriate; don't paper over it.
```

- [ ] **Step 2: Verify**

```bash
grep -c 'superpowers:' .claude/commands/opsx/apply.md
```

Expected: ≥ 4 (test-driven-development, requesting-code-review at group, verification-before-completion, plus references).

- [ ] **Step 3: Commit**

```bash
git add .claude/commands/opsx/apply.md
git commit -m "feat(opsx): apply.md invokes TDD + review skills at planned gates

session start → superpowers:test-driven-development
each group end → superpowers:requesting-code-review
final group → superpowers:verification-before-completion
Pattern matching on task prefixes (RED/GREEN/MOCK/VISUAL DIFF) routes
each task to the right action."
```

---

## Task 10: Rewrite `/opsx:archive` — 4 cleanup steps

**Files:**
- Modify: `.claude/commands/opsx/archive.md`

- [ ] **Step 1: Replace archive.md**

Write to `.claude/commands/opsx/archive.md`:

```markdown
---
name: "OPSX: Archive"
description: Archive a completed change + 4 cleanup steps the bare CLI doesn't do
category: Workflow
tags: [workflow, archive, experimental]
---

Run `openspec archive` and then perform the 4 cleanup steps that close the loop on capability docs and pitfall sinking.

**Input**: Optionally specify a change name. If omitted, infer or prompt.

---

**Steps**

### 1. Pre-flight: confirm the change is shipped

Run:

```bash
openspec status --change <name>
```

Every artifact must be `done`. Every task in `tasks.md` must be `- [x]`. If any are not, warn the user and ask for confirmation to proceed.

If delta specs exist at `openspec/changes/<name>/specs/`, show a sync summary (compare each delta with the corresponding `openspec/specs/<capability>/spec.md`):

> "Delta specs detected for capabilities: `<list>`. Sync now (recommended) | Archive without syncing | Cancel."

If sync chosen, invoke `openspec-sync-specs` via the Skill tool.

### 2. Run the archive

```bash
openspec archive <name>
```

Expected: change directory moves to `openspec/changes/archive/<date>-<name>/`. Capability specs at `openspec/specs/<capability>/spec.md` are created (if new) or updated (if delta).

### 3. Cleanup step 1 — fill capability spec `## Purpose`

`openspec archive` leaves a `## Purpose\nTBD - created by archiving change.` placeholder in any newly-created capability spec. Find them:

```bash
grep -l 'TBD - created by archiving' openspec/specs/*/spec.md
```

For each match, write a 1-3 sentence Purpose derived from:
- The change's `proposal.md` Why section
- The requirements doc's Goals section

Replace the placeholder. Commit when all are filled.

### 4. Cleanup step 2 — update `openspec/specs/README.md`

Open `openspec/specs/README.md`. Find the section listing capabilities. Add or update the entry for the new/modified capability. Use the existing format:

```markdown
### `<capability-name>` ✅ 已实现
**用户故事**: <one sentence>
**覆盖需求**: <requirement IDs>
**后台**: <bullet list>
**前台**: <bullet list>
**验收标准**: <one sentence>
```

If the format differs, follow the existing pattern in this specific README — don't impose your own.

### 5. Cleanup step 3 — update `CLAUDE.md` pitfalls

Read the change's `docs/log/<date>.md` entry (if it exists) and the change diff. If any non-obvious gotcha emerged (timing-sensitive bootstrap, env-var ordering, schema migration foot-gun, file-handling edge case), append a 2-3 line entry to the relevant section of `CLAUDE.md`'s Pitfalls.

If no new pitfall surfaced, skip this step. Don't fabricate pitfalls.

### 6. Cleanup step 4 — conditional project README

Decision: does this change introduce **user-visible** new features or behavior changes?

- Yes → ask the user: "This change introduces <description>. Do you want to update the project root README.md? Suggested addition: <draft>." Only update with user confirmation.
- No (operations / internals / infrastructure only) → skip.

Examples:
- `multi-user-auth-core` → YES (new login flow) → update README's "Getting Started" section
- `nas-deployment` → NO (ops change, no user-facing behavior) → skip
- `auth-rate-limiting` → NO (internal hardening, no UX change) → skip
- `multi-user-auth-admin-ui` → YES (new admin UI) → update README

### 7. Cleanup step 5 — dev log check

```bash
ls docs/log/<today>.md 2>/dev/null
```

If missing, prompt:

> "No dev log entry for today (`docs/log/<today>.md`). Want me to draft one based on this change? (Y/N)"

If Y, draft from the proposal + commits + review findings; let the user finalize. If N, skip.

### 8. Commit cleanup + final summary

```bash
git add openspec/specs/ CLAUDE.md README.md docs/log/
git commit -m "chore: archive <name> cleanup (Purpose, README, pitfalls, dev log)"
```

Output:

> "Change `<name>` archived. Workflow complete. Capability spec(s) at openspec/specs/<...>/. Archive at openspec/changes/archive/<date>-<name>/."

---

**Guardrails**

- NEVER skip Cleanup step 1 (Purpose). The TBD placeholder is the canonical example of what this rewrite is fixing.
- DO ask for confirmation before updating project README — that's user-facing surface.
- DO NOT fabricate pitfalls for CLAUDE.md if nothing genuinely surprised you in the change.
- DO commit cleanup steps as one atomic commit (not per-file) so the archive log is clean.
```

- [ ] **Step 2: Verify**

```bash
grep -c '^### [0-9]' .claude/commands/opsx/archive.md
```

Expected: `8` (eight numbered steps).

- [ ] **Step 3: Commit**

```bash
git add .claude/commands/opsx/archive.md
git commit -m "feat(opsx): archive.md adds 4 cleanup steps post-openspec-archive

After openspec archive runs:
1. Fill capability spec ## Purpose (replace TBD placeholder)
2. Update openspec/specs/README.md capability entry
3. Append to CLAUDE.md pitfalls if new gotcha surfaced
4. Conditionally update project README for user-visible changes
5. Dev log check + draft prompt
Single commit for the cleanup so archive history is clean."
```

---

## Task 11: Write the human overview workflow doc

**Files:**
- Create: `docs/superpowers/specs/2026-05-10-openspec-superpowers-workflow.md`

- [ ] **Step 1: Write the overview**

Write to `docs/superpowers/specs/2026-05-10-openspec-superpowers-workflow.md`:

```markdown
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

Reads context (proposal, specs, design, mocks, requirements). Invokes `superpowers:test-driven-development` at session start. Walks tasks; dispatches by prefix (RED / GREEN / MOCK / VISUAL DIFF / Run superpowers:requesting-code-review). Final group invokes `superpowers:verification-before-completion`.

Marks `- [x]` per-task immediately, not in batch.

## Phase 4: `/opsx:archive`

Runs `openspec archive` then 4 cleanups:

1. Fill capability spec `## Purpose` (the TBD placeholder is what this fixes)
2. Update `openspec/specs/README.md` capability entry
3. Append to `CLAUDE.md` pitfalls if a new gotcha surfaced
4. Conditionally update project root `README.md` (user-visible changes only)

Plus dev log check (`docs/log/<today>.md`).

## Where rules live (architecture)

| Concern | Lives in | Why |
|---|---|---|
| Artifact paths and dependencies | Schema (`schema.yaml`) | Static graph — schema is the right tool |
| Per-artifact prompt rules (TDD pattern, review checkpoints, MOCK/VISUAL DIFF sandwich) | Schema (per-artifact `instruction:`) | Inheritable; survives forks |
| Project context (tech stack, file paths, conventions) | `openspec/config.yaml` | Project-specific, not workflow-specific |
| Phase orchestration (Status: gate, Visual Companion, archive cleanup) | Slash commands | Actions, not artifacts |
| Skill invocation timing (when to call TDD / review / verification) | `.claude/commands/opsx/apply.md` | Execution-time decisions |

## Migration history

- 2026-05-10: schema forked from `spec-driven`; `requirements` + `mocks` artifacts added; rules migrated from `openspec/config.yaml` to schema instructions; 4 slash commands rewritten.
- In-flight `multi-user-auth-admin-ui` (created on `spec-driven`) keeps that schema until archived. Per-change schema is locked at change-creation time.
```

- [ ] **Step 2: Commit**

```bash
git add docs/superpowers/specs/2026-05-10-openspec-superpowers-workflow.md
git commit -m "docs: workflow overview for openspec-superpowers schema

Single human-readable entry point. Links into:
- design doc (why + architecture)
- implementation plan (this rollout)
- schema definition
- per-phase commands
- project context"
```

---

## Task 12: Smoke-test the full pipeline on a throwaway change

**Files:**
- Create (then delete): `openspec/changes/__workflow-smoke/`
- Create (then delete): `docs/superpowers/specs/2026-05-10-__workflow-smoke-requirements.md`
- Create (then delete): `docs/superpowers/specs/mocks/2026-05-10-__workflow-smoke-mocks.html`

- [ ] **Step 1: Manually create a `Status: REVIEWED` requirements doc**

Bypass `/opsx:explore` for the smoke (we're testing the propose/apply/archive path). Write to `docs/superpowers/specs/2026-05-10-__workflow-smoke-requirements.md`:

```markdown
---
Date: 2026-05-10
Change: __workflow-smoke
Status: REVIEWED
HAS_UI_SURFACE: no
---

# __workflow-smoke Requirements

## Goals
- Verify the superpowers-driven schema produces all artifacts when a change is proposed.

## Non-Goals
- This change is a test-only smoke. Will be deleted after verification.

## Constraints
- No actual code changes.

## Success Criteria
- `openspec status --change __workflow-smoke --json` shows all artifacts done.

## User Stories
- As the developer rolling out this workflow, I want to confirm the schema works end-to-end before declaring it done.

## Open Questions
- (none)

## Referenced Capabilities
- (none — smoke test only)
```

- [ ] **Step 2: Run propose end-to-end**

Manually run the steps that `/opsx:propose` would automate:

```bash
openspec new change __workflow-smoke --schema superpowers-driven
openspec status --change __workflow-smoke --json
```

The status should show `schemaName: superpowers-driven` and the artifact list. For each artifact other than `requirements` (which we wrote manually), generate it via instructions. For example, `proposal`:

```bash
openspec instructions proposal --change __workflow-smoke --json
```

Read the output, write `openspec/changes/__workflow-smoke/proposal.md` matching the template + instructions, with frontmatter `HAS_UI_SURFACE: no`. Repeat for `specs`, `design`, `mocks` (stub), `tasks`.

For the mocks stub, write to `docs/superpowers/specs/mocks/2026-05-10-__workflow-smoke-mocks.html`:

```html
<!DOCTYPE html>
<html><head><meta charset="UTF-8"><title>__workflow-smoke mocks</title></head>
<body><!-- HAS_UI_SURFACE: no -->
<p>This change has no UI surface; no visual mocks needed.</p>
</body></html>
```

For `tasks.md`, write a minimal TDD-shaped tasks file:

```markdown
## 1. Smoke test

- [ ] 1.1 RED — write a placeholder failing test
- [ ] 1.2 GREEN — make it pass
- [ ] 1.Z Run superpowers:requesting-code-review on the diff for group 1

## 2. Verification

- [ ] 2.1 Run superpowers:verification-before-completion
```

- [ ] **Step 3: Verify all artifacts done**

```bash
openspec status --change __workflow-smoke
```

Expected: every artifact `done`. If any is not, the schema's dependency graph or template rejected our content; debug.

- [ ] **Step 4: Verify the Status:REVIEWED gate**

Edit the requirements doc frontmatter, change `Status: REVIEWED` → `Status: DRAFT`, save. Re-run `openspec status --change __workflow-smoke --json` — note OpenSpec doesn't read this field, so the gate is enforced by `/opsx:propose`, not by openspec CLI.

Reset to `Status: REVIEWED`. This step just confirms the gate is the slash command's responsibility, not the CLI's.

- [ ] **Step 5: Cleanup**

```bash
rm -rf openspec/changes/__workflow-smoke
rm docs/superpowers/specs/2026-05-10-__workflow-smoke-requirements.md
rm docs/superpowers/specs/mocks/2026-05-10-__workflow-smoke-mocks.html
```

Verify the smoke change is gone:

```bash
openspec list
```

Expected: `__workflow-smoke` not present.

- [ ] **Step 6: Commit (only if smoke revealed real fixes)**

If the smoke revealed gaps in the schema or templates that needed fixes, commit those fixes:

```bash
git add openspec/schemas/superpowers-driven/
git commit -m "fix(schema): smoke-test fixes for superpowers-driven

<list specific fixes>"
```

If the smoke passed clean (no fixes needed), no commit at this task.

- [ ] **Step 7: Final commit — implementation plan complete**

```bash
git commit --allow-empty -m "chore: superpowers-driven workflow rollout complete

Schema: openspec/schemas/superpowers-driven/
Slash commands: .claude/commands/opsx/{explore,propose,apply,archive}.md
Workflow doc: docs/superpowers/specs/2026-05-10-openspec-superpowers-workflow.md

First real-world validation: nas-https change (per the design's
Validation section)."
```

---

## Self-Review

**Spec coverage:** Skimmed the spec section by section.

| Spec section | Implemented in task |
|---|---|
| Why / motivation | (background only — not a task) |
| Goals 1-5 | Tasks 2-3 (artifacts), Task 5 (TDD/review structure), Task 10 (archive cleanup), Task 7 (UI flow with awesome-design-md + Visual Companion) |
| Non-Goals | (informational — not a task) |
| Architecture diagram | Tasks 1-6 (schema + config) + Tasks 7-10 (commands) + Task 11 (workflow doc) |
| Schema artifact graph | Tasks 1-5 |
| Per-artifact instruction highlights | Tasks 2 (requirements), 3 (mocks), 4 (proposal), 5 (tasks) |
| Slash command behavior | Tasks 7-10 |
| Migration | Task 6 (config.yaml prune) — in-flight changes left on spec-driven (no migration task needed; OpenSpec locks per-change schema) |
| Validation: first real change | Out of scope of this plan — happens on the next real change (`nas-https`) |
| Roll-out order (8 steps in spec) | Tasks 1-12 cover those 8 plus smoke + final commit |
| Open questions | (informational — not a task) |
| Risks / Trade-offs | R-01 (schema drift), R-02 (command divergence), R-03 (rigid for small fixes), R-04 (Status gate bypass) — mitigations are documented in the workflow doc (Task 11), not implemented as code |

**Placeholder scan:** Searched for "TBD", "TODO", "implement later", "Add appropriate". None found in the plan body. The known unknown about Branch P/C is explicit and resolved in Task 1.

**Type consistency:** Cross-referenced names across tasks:
- `superpowers-driven` schema name — consistent everywhere
- `requirements`, `proposal`, `specs`, `design`, `mocks`, `tasks` — artifact IDs consistent
- `HAS_UI_SURFACE` field name — consistent (Tasks 2, 3, 4, 7, 8, 12)
- `Status: DRAFT` / `Status: REVIEWED` — consistent (Tasks 2, 7, 8, 12)
- File paths — `docs/superpowers/specs/<date>-<topic>-requirements.md` consistent (Tasks 2, 7, 8, 11, 12)
- `<date>` placeholder is `YYYY-MM-DD` everywhere
- `<topic>` and `<change>` are used interchangeably; this is intentional — they're the same string (kebab-case), but `<topic>` reads more naturally when discussed in commands and `<change>` when discussed in schema templates. Documented in Task 11's workflow doc.

No issues found.

---

## Plan complete

Plan saved to `docs/superpowers/plans/2026-05-10-openspec-superpowers-workflow.md`.
