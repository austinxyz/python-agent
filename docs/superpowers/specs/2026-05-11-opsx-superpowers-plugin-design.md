# opsx-superpowers Plugin — Design Document

**Date:** 2026-05-11  
**Status:** REVIEWED  
**Author:** Austin  

---

## Context

The current OpenSpec + Superpowers workflow (`superpowers-driven` schema + four `/opsx:*` commands) lives entirely inside `python-agent`. It works well but is not portable: schema files, slash commands, and project-specific content (test commands, design system tokens, LangGraph rules) are all mixed together in one place.

This design extracts the generic workflow into a standalone ECC plugin (`opsx-superpowers`) while keeping project-specific configuration in each project's `openspec/config.yaml`.

**Prior art:** `docs/openspec-workflow.md` already documents a "Cross-project reuse" section with this exact refactor as a future recommendation. This design executes it.

---

## Goals

- Package the superpowers-driven OpenSpec workflow as an installable ECC plugin
- Remove all `python-agent`-specific content from the schema and slash commands
- New project setup: install plugin → run `opsx-install` → fill in `config.yaml`
- python-agent migrates cleanly with zero workflow change (same `/opsx:*` commands)

## Non-Goals

- Changing the four-phase workflow itself (`explore → propose → apply → archive`)
- Publishing to an ECC official plugin registry (GitHub install is sufficient)
- Supporting non-Claude Code environments

---

## Decisions

### 1. Repo name: `opsx-superpowers`

**Why not `opsx`**: Official OpenSpec CLI installs commands under the `opsx` namespace — naming the repo `opsx` implies this is the official tool.  
**Why not `superspec` / `openspec-superpowers`**: `opsx-superpowers` makes the relationship explicit: this is the superpowers-enhanced layer on top of `opsx`.

### 2. ECC plugin, not user-level file copy

**Alternatives considered:**
- **User-level file promotion** (already documented in `openspec-workflow.md`): works but no upgrade path
- **Git submodule**: upgrade path exists but adds git complexity to consumer projects
- **ECC plugin**: upgrade via plugin manager, clean separation, standard distribution format → chosen

### 3. Schema distribution via `bin/opsx-install`

ECC plugins cannot write to arbitrary filesystem paths. OpenSpec CLI resolves schemas from:
1. Project-level `openspec/schemas/`
2. User-level `~/.local/share/openspec/schemas/` (Linux/Mac) or `%APPDATA%\openspec\schemas\` (Windows)

Solution: bundle schema files in the plugin under `schemas/` and ship a `bin/opsx-install` script that promotes them to user-level on first install and after upgrades.

**Why not project-level schema per consumer project**: defeats the purpose — changes to the schema would require updating every project manually.

### 4. Project-specific content moves to `config.yaml project:` section (structured YAML)

**Alternatives considered:**
- Natural language in `context:` section: flexible but AI parsing is unreliable for command substitution
- Separate `project.yaml` file: adds a file with no benefit over a section in existing `config.yaml`

Structured YAML keys are unambiguous for slash commands to read and substitute.

### 5. Slash commands stay in `commands/opsx/`, not `skills/`

`/opsx:*` are user-invoked workflows. ECC `commands/` is the right home. Skills are model-invoked.

---

## New Repo Structure: `opsx-superpowers`

```
opsx-superpowers/
├── .claude-plugin/
│   └── plugin.json                  # name: opsx-superpowers, version: 1.0.0
├── commands/
│   └── opsx/
│       ├── explore.md               # generic (no project content)
│       ├── propose.md               # generic
│       ├── apply.md                 # reads config.yaml project section at start
│       └── archive.md               # generic
├── schemas/
│   └── superpowers-driven/
│       ├── schema.yaml              # LangGraph rule removed
│       └── templates/
│           ├── tasks.md             # {{project.*}} placeholders
│           ├── proposal.md
│           ├── requirements.md
│           ├── spec.md
│           ├── design.md
│           └── mocks.html
├── bin/
│   └── opsx-install                 # promotes schema to user-level
├── config-template.yaml             # starter template for new projects
└── README.md                        # installation + new project setup guide
```

---

## Files to Change

### `schema.yaml` (1 change)

Remove from `tasks` instruction:

```yaml
# REMOVE:
**LangGraph rule:** graph tasks MUST test nodes independently (unit)
before testing the full graph flow (integration).
```

This moves to python-agent's `config.yaml` under `rules.tasks`.

### `templates/tasks.md` (3 changes)

| Before | After |
|---|---|
| `bring up dev stack (npm run dev:up)` | `bring up dev stack (project.dev_stack_command from config.yaml)` |
| `note Notion tokens (bg-notion-*, text-notion-*)` | `note design system tokens (project.design_system from config.yaml)` |
| `cd backend && pytest; cd frontend && npm test` | `run project.test_commands from config.yaml` |
| Qdrant `user_id` grep | `run project.custom_verification_checks from config.yaml` |

### `apply.md` (add Setup block at top of Steps)

```markdown
**Setup**: Read `openspec/config.yaml` `project` section before starting:
- `project.dev_stack_command` — used when bringing up dev stack (VISUAL DIFF tasks)
- `project.test_commands` — used in final verification step
- `project.custom_verification_checks` — appended to verification-before-completion
- `project.design_system` — referenced in MOCK tasks for token naming
```

### `bin/opsx-install` (new file)

```bash
#!/usr/bin/env bash
set -e
PLUGIN_DIR="$(cd "$(dirname "$0")/.." && pwd)"
SCHEMA_SRC="$PLUGIN_DIR/schemas/superpowers-driven"

if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" || -n "$APPDATA" ]]; then
  SCHEMA_DST="$APPDATA/openspec/schemas/superpowers-driven"
else
  SCHEMA_DST="${XDG_DATA_HOME:-$HOME/.local/share}/openspec/schemas/superpowers-driven"
fi

mkdir -p "$(dirname "$SCHEMA_DST")"
cp -r "$SCHEMA_SRC" "$SCHEMA_DST"
echo "✓ superpowers-driven schema installed to $SCHEMA_DST"
echo "  Verify: openspec schemas"
```

### `config-template.yaml` (new file)

```yaml
schema: superpowers-driven

project:
  dev_stack_command: ""          # e.g. "docker compose up -d" or "npm run dev"
  test_commands:
    - ""                         # e.g. "pytest" / "go test ./..." / "npm test"
  e2e_command: ""                # optional, e.g. "npm run e2e"
  design_system: "notion"        # notion | linear | custom
  custom_verification_checks: [] # project-specific grep/lint checks for final verification

context: |
  # Describe your project:
  # - Tech stack and versions
  # - Directory structure
  # - Test setup (frameworks, how to run)
  # - Key conventions (naming, error handling, etc.)

rules: {}
  # Add per-artifact rules here, e.g.:
  # tasks:
  #   - "Your custom rule for task generation"
  # design:
  #   - "Your custom rule for design docs"
```

---

## python-agent `config.yaml` Changes

Add `project:` section and move LangGraph rule to `rules.tasks`:

```yaml
schema: superpowers-driven

project:
  dev_stack_command: "npm run dev:up"
  test_commands:
    - "cd backend && pytest"
    - "cd frontend && npm test"
  e2e_command: "cd frontend && npm run e2e"
  design_system: "notion"
  custom_verification_checks:
    - 'grep -rn "search_private\|qdrant.*private" backend/app --include="*.py" | grep -v "user_id"'

rules:
  tasks:
    - "LangGraph rule: graph tasks MUST test nodes independently (unit) before testing the full graph flow (integration)."
  proposal:
    # (existing rules unchanged)
  design:
    # (existing rules unchanged)
  specs:
    # (existing rules unchanged)

context: |
  # (existing content unchanged)
```

---

## python-agent Migration Steps

1. Install plugin: `claude --plugin-url https://github.com/<user>/opsx-superpowers`
2. Run `opsx-install` once to promote schema to user-level
3. Update `openspec/config.yaml`: add `project:` section, add `rules.tasks` LangGraph rule
4. Delete project-level schema: `rm -rf openspec/schemas/superpowers-driven/`
5. Delete project-level commands: `rm -rf .claude/commands/opsx/`
6. Verify: `openspec schemas` shows `superpowers-driven` at user-level; `/opsx:explore` still works

---

## New Project Setup (after plugin installed)

```bash
cd my-new-project
openspec init
cp $(claude --plugin-dir opsx-superpowers)/config-template.yaml openspec/config.yaml
# Edit config.yaml: fill in project.dev_stack_command, test_commands, context
```

---

## Risks / Trade-offs

| Risk | Mitigation |
|---|---|
| `opsx-install` must be re-run after plugin upgrade | Document clearly in README; consider adding a version check |
| Consumer projects on old schema after plugin update | Semantic versioning in `plugin.json`; changelog in README |
| `bin/opsx-install` path resolution differs on Windows (Git Bash vs PowerShell) | Script detects `$APPDATA` env var; tested on both |
| python-agent loses project-level schema override ability | Can always add back a project-level `openspec/schemas/` to override |

---

## Open Questions

None — all decisions locked above.
