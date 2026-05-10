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

Order: `proposal` → `specs` → `design` → `mocks` → `tasks`.
(`requirements` was created in `/opsx:explore`; openspec sees it as `done`.)

**Path resolution caveat:** the `outputPath` returned by `openspec instructions` for `requirements` and `mocks` artifacts contains literal `{{date}}` and `{{change}}` strings (OpenSpec does NOT auto-substitute). You must substitute them before writing the file. For example, `outputPath: "../../../docs/superpowers/specs/{{date}}-{{change}}-requirements.md"` with `date=2026-05-10`, `change=multi-user-auth-core` resolves to `docs/superpowers/specs/2026-05-10-multi-user-auth-core-requirements.md`.

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
git add openspec/changes/<topic>/
# Only if HAS_UI_SURFACE: yes AND the mocks file hasn't already been committed in /opsx:explore Phase 5:
git add docs/superpowers/specs/mocks/*-<topic>-mocks.html
git commit -m "docs: propose <topic> change"
```

Verify with `git status` before committing — the second `git add` is conditional. For backend-only changes (`HAS_UI_SURFACE: no`), the mocks file may already be the stub from `/opsx:propose` Step 3 (mocks artifact generation) or absent entirely; check before staging.

Output:

> "Change `<topic>` proposed. Artifacts: requirements (in docs/), proposal, specs, design, mocks, tasks. Next: `/opsx:apply <topic>`."

---

**Guardrails**

- NEVER bypass the Status: REVIEWED check. If the user insists, send them back to `/opsx:explore` Phase 3.
- NEVER write artifacts that the schema would generate via `openspec instructions`. Always go through the CLI.
- If a change with that name already exists at `openspec/changes/<topic>/`, ask the user whether to continue (delete and re-create) or pick a different name.
- `context` and `rules` from `openspec instructions` output are constraints on YOU (the agent), not content to copy into artifact files.
