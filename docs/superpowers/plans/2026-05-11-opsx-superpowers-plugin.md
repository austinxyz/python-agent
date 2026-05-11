# opsx-superpowers Plugin Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extract the superpowers-driven OpenSpec workflow from python-agent into a standalone installable ECC plugin at `C:\Users\lorra\projects\opsx-superpowers`, then migrate python-agent to use it.

**Architecture:** Two phases — Phase 1 creates the `opsx-superpowers` repo (generic schema + commands + install script). Phase 2 migrates python-agent (adds `project:` config, removes project-level schema/commands, installs plugin).

**Tech Stack:** Bash (bin script), YAML (schema + config), Markdown (commands/templates), ECC plugin format

---

## File Map

**New repo `C:\Users\lorra\projects\opsx-superpowers\`:**

| File | Action | Notes |
|---|---|---|
| `.claude-plugin/plugin.json` | Create | Plugin manifest |
| `commands/opsx/explore.md` | Copy from python-agent | No changes needed |
| `commands/opsx/propose.md` | Copy from python-agent | No changes needed |
| `commands/opsx/apply.md` | Copy + edit | Add Setup block, update VISUAL DIFF dispatch |
| `commands/opsx/archive.md` | Copy from python-agent | No changes needed |
| `schemas/superpowers-driven/schema.yaml` | Copy + edit | Remove LangGraph rule from tasks instruction |
| `schemas/superpowers-driven/templates/tasks.md` | Copy + edit | Replace hardcoded commands with config.yaml references |
| `schemas/superpowers-driven/templates/proposal.md` | Copy | No changes |
| `schemas/superpowers-driven/templates/requirements.md` | Copy | No changes |
| `schemas/superpowers-driven/templates/spec.md` | Copy | No changes |
| `schemas/superpowers-driven/templates/design.md` | Copy | No changes |
| `schemas/superpowers-driven/templates/mocks.html` | Copy | No changes |
| `bin/opsx-install` | Create | Schema promotion script |
| `config-template.yaml` | Create | Starter config for new projects |
| `README.md` | Create | Install + new project + upgrade guide |

**Modified in python-agent:**

| File | Action |
|---|---|
| `openspec/config.yaml` | Add `project:` section + `rules.tasks` LangGraph rule |
| `openspec/schemas/superpowers-driven/` | Delete (after plugin verified) |
| `.claude/commands/opsx/` | Delete (after plugin verified) |
| `docs/openspec-workflow.md` | Update distribution section to reference plugin |

---

## Phase 1 — Create opsx-superpowers repo

---

### Task 1: Initialize repo + plugin manifest

**Files:**
- Create: `C:\Users\lorra\projects\opsx-superpowers\`
- Create: `C:\Users\lorra\projects\opsx-superpowers\.claude-plugin\plugin.json`

- [ ] **Step 1: Create directory and initialize git**

```powershell
New-Item -ItemType Directory -Path "C:\Users\lorra\projects\opsx-superpowers"
cd C:\Users\lorra\projects\opsx-superpowers
git init
```

- [ ] **Step 2: Create plugin manifest**

Create `.claude-plugin/plugin.json`:

```json
{
  "name": "opsx-superpowers",
  "version": "1.0.0",
  "description": "OpenSpec workflow with built-in TDD + code review gates for Claude Code. Four-phase: explore → propose → apply → archive.",
  "author": {
    "name": "austinxyz"
  }
}
```

- [ ] **Step 3: Create directory scaffold**

```bash
mkdir -p .claude-plugin commands/opsx schemas/superpowers-driven/templates bin
```

- [ ] **Step 4: Initial commit**

```bash
git add .claude-plugin/plugin.json
git commit -m "chore: init opsx-superpowers plugin"
```

---

### Task 2: Copy + generalize schema.yaml

**Files:**
- Source: `C:\Users\lorra\projects\python-agent\openspec\schemas\superpowers-driven\schema.yaml`
- Create: `C:\Users\lorra\projects\opsx-superpowers\schemas\superpowers-driven\schema.yaml`

The only change: remove the LangGraph-specific sentence from the `tasks` instruction.

- [ ] **Step 1: Copy schema.yaml**

```powershell
Copy-Item "C:\Users\lorra\projects\python-agent\openspec\schemas\superpowers-driven\schema.yaml" `
  "C:\Users\lorra\projects\opsx-superpowers\schemas\superpowers-driven\schema.yaml"
```

- [ ] **Step 2: Remove LangGraph rule**

Open `schemas/superpowers-driven/schema.yaml`. Find this block in the `tasks` instruction (around line 268) and delete the two lines:

```yaml
      **LangGraph rule:** graph tasks MUST test nodes independently (unit)
      before testing the full graph flow (integration).
```

The tasks instruction should end with the `Skill names:` paragraph after this removal. Verify the surrounding lines look correct and no other content was accidentally removed.

- [ ] **Step 3: Commit**

```bash
git add schemas/superpowers-driven/schema.yaml
git commit -m "feat: add generalized superpowers-driven schema"
```

---

### Task 3: Copy + generalize templates/tasks.md

**Files:**
- Source: `C:\Users\lorra\projects\python-agent\openspec\schemas\superpowers-driven\templates\tasks.md`
- Create: `C:\Users\lorra\projects\opsx-superpowers\schemas\superpowers-driven\templates\tasks.md`

Four substitutions — replacing hardcoded python-agent content with config.yaml references.

- [ ] **Step 1: Copy tasks.md**

```powershell
Copy-Item "C:\Users\lorra\projects\python-agent\openspec\schemas\superpowers-driven\templates\tasks.md" `
  "C:\Users\lorra\projects\opsx-superpowers\schemas\superpowers-driven\templates\tasks.md"
```

- [ ] **Step 2: Apply substitution 1 — VISUAL DIFF line**

Find:
```
- [ ] 2.4 VISUAL DIFF — bring up dev stack (npm run dev:up); navigate to the route; eyeball rendered UI against the mock; fix any token/color/text drift
```

Replace with:
```
- [ ] 2.4 VISUAL DIFF — bring up dev stack (use project.dev_stack_command from openspec/config.yaml); navigate to the route; eyeball rendered UI against the mock; fix any token/color/text drift
```

- [ ] **Step 3: Apply substitution 2 — MOCK line tokens**

Find:
```
- [ ] 2.1 MOCK — open docs/superpowers/specs/mocks/{{date}}-{{change}}-mocks.html#<anchor>; note Notion tokens used (bg-notion-*, text-notion-*) and verbatim text strings
```

Replace with:
```
- [ ] 2.1 MOCK — open docs/superpowers/specs/mocks/{{date}}-{{change}}-mocks.html#<anchor>; note design system tokens (see project.design_system in openspec/config.yaml) and verbatim text strings
```

- [ ] **Step 4: Apply substitution 3 — test suite lines**

Find:
```
- [ ] 3.1 Run full pytest suite — ensure no regressions
- [ ] 3.2 Run full vitest suite — ensure no regressions
- [ ] 3.3 Run Playwright e2e suite (if applicable)
```

Replace with:
```
- [ ] 3.1 Run backend test suite — ensure no regressions (use project.test_commands from openspec/config.yaml)
- [ ] 3.2 Run frontend test suite — ensure no regressions (use project.test_commands from openspec/config.yaml)
- [ ] 3.3 Run e2e suite if applicable (use project.e2e_command from openspec/config.yaml)
```

- [ ] **Step 5: Apply substitution 4 — verification-before-completion line**

Find:
```
- [ ] 3.4 Run superpowers:verification-before-completion (cd backend && pytest; cd frontend && npm test; grep -r console.log frontend/src; diff review; grep -rn "search_private\|qdrant.*private" backend/app --include="*.py" | grep -v "user_id" — ensure no Qdrant private query is missing the user_id filter)
```

Replace with:
```
- [ ] 3.4 Run superpowers:verification-before-completion (run project.test_commands from openspec/config.yaml; grep -r console.log on frontend src if applicable; run project.custom_verification_checks from openspec/config.yaml)
```

- [ ] **Step 6: Commit**

```bash
git add schemas/superpowers-driven/templates/tasks.md
git commit -m "feat: generalize tasks template — config-driven commands"
```

---

### Task 4: Copy + generalize apply.md

**Files:**
- Source: `C:\Users\lorra\projects\python-agent\.claude\commands\opsx\apply.md`
- Create: `C:\Users\lorra\projects\opsx-superpowers\commands\opsx\apply.md`

Two changes: add Setup block, update VISUAL DIFF dispatch to reference config.yaml.

- [ ] **Step 1: Copy apply.md**

```powershell
Copy-Item "C:\Users\lorra\projects\python-agent\.claude\commands\opsx\apply.md" `
  "C:\Users\lorra\projects\opsx-superpowers\commands\opsx\apply.md"
```

- [ ] **Step 2: Add Setup block**

After the `---` separator line that follows the `**Input**:` paragraph (i.e., right before `**Steps**`), insert:

```markdown
**Setup**: Before starting, read `openspec/config.yaml` and note the `project` section:
- `project.dev_stack_command` — command to bring up the dev stack (used in VISUAL DIFF tasks)
- `project.test_commands` — list of test commands (used in verification step)
- `project.e2e_command` — e2e test command (optional)
- `project.custom_verification_checks` — appended to verification-before-completion
- `project.design_system` — design system name (referenced in MOCK tasks for token naming)

---
```

- [ ] **Step 3: Update VISUAL DIFF dispatch**

Find:
```
- **`- [ ] N.X VISUAL DIFF — ...`** → bring up the dev stack (`npm run dev:up` or whatever the task says), navigate to the route, eyeball the rendered UI against the mock. Fix any token/color/text drift. Mark the checkbox.
```

Replace with:
```
- **`- [ ] N.X VISUAL DIFF — ...`** → bring up the dev stack (`project.dev_stack_command` from `openspec/config.yaml`, or whatever the task says), navigate to the route, eyeball the rendered UI against the mock. Fix any token/color/text drift. Mark the checkbox.
```

- [ ] **Step 4: Commit**

```bash
git add commands/opsx/apply.md
git commit -m "feat: add apply command with config-driven setup"
```

---

### Task 5: Copy remaining commands (no changes)

**Files:** explore.md, propose.md, archive.md — all generic, copy as-is.

- [ ] **Step 1: Copy three commands**

```powershell
$src = "C:\Users\lorra\projects\python-agent\.claude\commands\opsx"
$dst = "C:\Users\lorra\projects\opsx-superpowers\commands\opsx"
Copy-Item "$src\explore.md" "$dst\explore.md"
Copy-Item "$src\propose.md" "$dst\propose.md"
Copy-Item "$src\archive.md" "$dst\archive.md"
```

- [ ] **Step 2: Verify no python-agent-specific content leaked in**

```bash
grep -n "npm run dev:up\|bg-notion\|cd backend\|cd frontend\|qdrant\|LangGraph" \
  commands/opsx/explore.md commands/opsx/propose.md commands/opsx/archive.md
```

Expected: no output (zero matches).

- [ ] **Step 3: Commit**

```bash
git add commands/opsx/explore.md commands/opsx/propose.md commands/opsx/archive.md
git commit -m "feat: add explore, propose, archive commands"
```

---

### Task 6: Copy remaining templates (no changes)

**Files:** proposal.md, requirements.md, spec.md, design.md, mocks.html — all generic.

- [ ] **Step 1: Copy five templates**

```powershell
$src = "C:\Users\lorra\projects\python-agent\openspec\schemas\superpowers-driven\templates"
$dst = "C:\Users\lorra\projects\opsx-superpowers\schemas\superpowers-driven\templates"
Copy-Item "$src\proposal.md"     "$dst\proposal.md"
Copy-Item "$src\requirements.md" "$dst\requirements.md"
Copy-Item "$src\spec.md"         "$dst\spec.md"
Copy-Item "$src\design.md"       "$dst\design.md"
Copy-Item "$src\mocks.html"      "$dst\mocks.html"
```

- [ ] **Step 2: Commit**

```bash
git add schemas/superpowers-driven/templates/
git commit -m "feat: add schema templates"
```

---

### Task 7: Create bin/opsx-install

**Files:**
- Create: `C:\Users\lorra\projects\opsx-superpowers\bin\opsx-install`

- [ ] **Step 1: Write the install script**

Create `bin/opsx-install` with this exact content:

```bash
#!/usr/bin/env bash
set -e

PLUGIN_DIR="$(cd "$(dirname "$0")/.." && pwd)"
SCHEMA_SRC="$PLUGIN_DIR/schemas/superpowers-driven"

# Windows (Git Bash / MSYS) uses $APPDATA
if [[ -n "$APPDATA" ]]; then
  SCHEMA_DST="$APPDATA/openspec/schemas/superpowers-driven"
else
  # Linux / Mac
  SCHEMA_DST="${XDG_DATA_HOME:-$HOME/.local/share}/openspec/schemas/superpowers-driven"
fi

if [[ ! -d "$SCHEMA_SRC" ]]; then
  echo "ERROR: Schema source not found at $SCHEMA_SRC" >&2
  exit 1
fi

mkdir -p "$(dirname "$SCHEMA_DST")"

if [[ -d "$SCHEMA_DST" ]]; then
  echo "Updating existing schema at $SCHEMA_DST..."
  rm -rf "$SCHEMA_DST"
fi

cp -r "$SCHEMA_SRC" "$SCHEMA_DST"
echo "✓ superpowers-driven schema installed to $SCHEMA_DST"
echo "  Verify: openspec schemas"
```

- [ ] **Step 2: Make executable**

```bash
chmod +x bin/opsx-install
```

- [ ] **Step 3: Smoke test the script locally**

```bash
./bin/opsx-install
```

Expected output:
```
✓ superpowers-driven schema installed to /path/to/openspec/schemas/superpowers-driven
  Verify: openspec schemas
```

- [ ] **Step 4: Verify OpenSpec can see the schema**

```bash
openspec schemas
```

Expected: `superpowers-driven` appears in the list.

- [ ] **Step 5: Commit**

```bash
git add bin/opsx-install
git commit -m "feat: add opsx-install schema promotion script"
```

---

### Task 8: Create config-template.yaml

**Files:**
- Create: `C:\Users\lorra\projects\opsx-superpowers\config-template.yaml`

- [ ] **Step 1: Write config-template.yaml**

```yaml
schema: superpowers-driven

project:
  dev_stack_command: ""          # e.g. "docker compose up -d" or "npm run dev"
  test_commands:
    - ""                         # e.g. "pytest" / "go test ./..." / "npm test"
  e2e_command: ""                # optional, e.g. "npm run e2e" — leave empty to skip
  design_system: "notion"        # notion | linear | custom
  custom_verification_checks: [] # project-specific grep/lint checks appended to final verification
                                 # e.g. 'grep -rn "hardcoded_secret" src/'

context: |
  # Describe your project so Claude understands it. Include:
  # - Tech stack and versions (e.g. "Python 3.12 + FastAPI + PostgreSQL")
  # - Directory structure (e.g. "backend/app/, frontend/src/")
  # - How to run tests (e.g. "pytest from repo root, vitest from frontend/")
  # - Key conventions (naming, error handling, auth patterns)
  # - Any shared components or patterns Claude should reuse
  # This context is injected into every artifact generation prompt.

rules: {}
  # Per-artifact rules appended to artifact-specific instructions.
  # Examples:
  # tasks:
  #   - "Django rule: use pytest-django fixtures; never instantiate models without factory_boy."
  # design:
  #   - "For any database change: state migration strategy and rollback plan."
  # specs:
  #   - "All API endpoints SHALL document authentication requirements."
```

- [ ] **Step 2: Commit**

```bash
git add config-template.yaml
git commit -m "feat: add config-template.yaml for new project setup"
```

---

### Task 9: Create README.md

**Files:**
- Create: `C:\Users\lorra\projects\opsx-superpowers\README.md`

- [ ] **Step 1: Write README.md**

```markdown
# opsx-superpowers

OpenSpec workflow with built-in TDD + code review gates for Claude Code.

Four-phase development discipline:

```
/opsx:explore <topic>   → discuss → requirements.md (DRAFT → REVIEWED)
/opsx:propose <topic>   → proposal + specs + design + tasks
/opsx:apply <topic>     → TDD execution + code review gates
/opsx:archive <topic>   → archive + capability spec + CLAUDE.md
```

Each phase is a hard boundary. You cannot skip phases.

## Install

### 1. Install the plugin

```bash
claude --plugin-url https://github.com/austinxyz/opsx-superpowers
```

### 2. Promote the schema (run once, and after each upgrade)

```bash
opsx-install
```

Verify: `openspec schemas` should list `superpowers-driven`.

## New Project Setup

```bash
cd my-project
openspec init
# Copy the starter config
cp ~/.claude/plugins/.../config-template.yaml openspec/config.yaml
# Edit openspec/config.yaml — fill in your project section and context
```

Minimum `openspec/config.yaml`:

```yaml
schema: superpowers-driven

project:
  dev_stack_command: "docker compose up -d"
  test_commands:
    - "pytest"
  design_system: "notion"

context: |
  Tech stack: Python + FastAPI + PostgreSQL
  Tests: pytest from repo root
```

Then start your first change:

```
/opsx:explore my-first-feature
```

## Upgrading

```bash
# Pull latest plugin
claude --plugin-url https://github.com/austinxyz/opsx-superpowers

# Re-promote the schema (required after every upgrade)
opsx-install
```

## What goes in config.yaml

| Key | Purpose | Example |
|---|---|---|
| `project.dev_stack_command` | Bring up local dev environment | `"npm run dev:up"` |
| `project.test_commands` | List of test commands | `["pytest", "npm test"]` |
| `project.e2e_command` | E2E test command (optional) | `"npm run e2e"` |
| `project.design_system` | Design system for UI mocks | `"notion"` or `"linear"` |
| `project.custom_verification_checks` | Project-specific checks in final verification | `["grep -rn 'secret' src/"]` |
| `context` | Project description for Claude | Natural language |
| `rules` | Per-artifact generation rules | See config-template.yaml |

## Does this conflict with official OpenSpec commands?

No. Official OpenSpec uses the `openspec-*` prefix. This plugin uses `opsx:*`. Zero collision.
```

- [ ] **Step 2: Commit**

```bash
git add README.md
git commit -m "docs: add README with install and usage guide"
```

---

### Task 10: Push to GitHub (manual step)

- [ ] **Step 1: Create GitHub repo**

Go to https://github.com/new — create `opsx-superpowers`, public, no template.

- [ ] **Step 2: Push**

```bash
git remote add origin https://github.com/austinxyz/opsx-superpowers.git
git branch -M main
git push -u origin main
```

- [ ] **Step 3: Note the plugin URL for next phase**

The install URL will be:
```
https://github.com/austinxyz/opsx-superpowers
```

---

## Phase 2 — Migrate python-agent

---

### Task 11: Update python-agent config.yaml

**Files:**
- Modify: `C:\Users\lorra\projects\python-agent\openspec\config.yaml`

- [ ] **Step 1: Open config.yaml**

The file currently starts with `schema: superpowers-driven` then `context: |`.

- [ ] **Step 2: Add project: section**

After the `schema: superpowers-driven` line and before `context: |`, insert:

```yaml
project:
  dev_stack_command: "npm run dev:up"
  test_commands:
    - "cd backend && pytest"
    - "cd frontend && npm test"
  e2e_command: "cd frontend && npm run e2e"
  design_system: "notion"
  custom_verification_checks:
    - 'grep -rn "search_private\|qdrant.*private" backend/app --include="*.py" | grep -v "user_id"'

```

- [ ] **Step 3: Add LangGraph rule to rules section**

The file has a `rules:` key. Add `tasks:` under it:

```yaml
rules:
  tasks:
    - "LangGraph rule: graph tasks MUST test nodes independently (unit) before testing the full graph flow (integration)."
  proposal:
    # (existing entries unchanged)
  ...
```

- [ ] **Step 4: Verify YAML is valid**

```bash
python -c "import yaml; yaml.safe_load(open('openspec/config.yaml'))" && echo "YAML valid"
```

Expected: `YAML valid`

- [ ] **Step 5: Commit**

```bash
cd C:\Users\lorra\projects\python-agent
git add openspec/config.yaml
git commit -m "chore: add project: section to config.yaml for opsx-superpowers plugin"
```

---

### Task 12: Install plugin + run opsx-install + verify

- [ ] **Step 1: Install plugin**

Run in terminal (not Claude Code):
```bash
claude --plugin-url https://github.com/austinxyz/opsx-superpowers
```

Expected: plugin installed confirmation.

- [ ] **Step 2: Run opsx-install to promote schema**

```bash
opsx-install
```

Expected:
```
✓ superpowers-driven schema installed to C:\Users\lorra\AppData\Roaming\openspec\schemas\superpowers-driven
  Verify: openspec schemas
```

- [ ] **Step 3: Verify schema visible at user-level**

```bash
openspec schemas
```

Expected: `superpowers-driven` listed with `Source: user`.

- [ ] **Step 4: Smoke test workflow still works**

In Claude Code, run:
```
/opsx:explore smoke-test
```

Expected: `/opsx:explore` activates, Claude starts Phase 1 explore mode. Abort after confirming it starts correctly (no need to complete the change).

```bash
# Clean up smoke test if any files were created
rm -f docs/superpowers/specs/*-smoke-test-requirements.md
```

---

### Task 13: Delete project-level schema + commands + verify

Only do this after Task 12 verifies the plugin works.

**Files to delete:**
- `C:\Users\lorra\projects\python-agent\openspec\schemas\superpowers-driven\`
- `C:\Users\lorra\projects\python-agent\.claude\commands\opsx\`

- [ ] **Step 1: Delete project-level schema**

```powershell
Remove-Item -Recurse -Force "C:\Users\lorra\projects\python-agent\openspec\schemas\superpowers-driven"
```

- [ ] **Step 2: Verify OpenSpec still resolves schema (falls back to user-level)**

```bash
cd C:\Users\lorra\projects\python-agent
openspec schemas
```

Expected: `superpowers-driven` still listed (now from user-level).

- [ ] **Step 3: Delete project-level commands**

```powershell
Remove-Item -Recurse -Force "C:\Users\lorra\projects\python-agent\.claude\commands\opsx"
```

- [ ] **Step 4: Final smoke test**

In Claude Code within python-agent:
```
/opsx:explore smoke-test-2
```

Expected: `/opsx:explore` activates from plugin (same behavior). Abort after confirming.

```bash
rm -f docs/superpowers/specs/*-smoke-test-2-requirements.md
```

- [ ] **Step 5: Commit cleanup**

```bash
git add -A
git commit -m "chore: migrate to opsx-superpowers plugin — remove project-level schema + commands"
```

---

### Task 14: Update openspec-workflow.md distribution section

**Files:**
- Modify: `C:\Users\lorra\projects\python-agent\docs\openspec-workflow.md`

- [ ] **Step 1: Update the 跨项目复用 section**

Find the `## 跨项目复用` section. Replace the three-option table and the manual copy instructions with:

```markdown
## 跨项目复用

`superpowers-driven` schema 和 `/opsx:*` commands 现在通过 [`opsx-superpowers`](https://github.com/austinxyz/opsx-superpowers) ECC plugin 分发。

### 安装

```bash
# 1. 安装 plugin
claude --plugin-url https://github.com/austinxyz/opsx-superpowers

# 2. 把 schema promote 到 user-level（装完和每次升级后都要跑）
opsx-install

# 验证
openspec schemas   # 应该列出 superpowers-driven（Source: user）
```

### 新项目初始化

```bash
cd my-project
openspec init
# 从 plugin 的 config-template.yaml 复制初始配置
cp <plugin-dir>/config-template.yaml openspec/config.yaml
# 编辑 openspec/config.yaml：填 project 节和 context
```

最小 `openspec/config.yaml`：

```yaml
schema: superpowers-driven

project:
  dev_stack_command: "your-dev-stack-command"
  test_commands:
    - "your-test-command"
  design_system: "notion"

context: |
  # 你的项目描述
```

### 升级

```bash
claude --plugin-url https://github.com/austinxyz/opsx-superpowers
opsx-install   # 每次升级后重新 promote schema
```
```

- [ ] **Step 2: Commit**

```bash
git add docs/openspec-workflow.md
git commit -m "docs: update workflow guide — plugin-based distribution"
```

---

## Spec Coverage Check

| Design requirement | Task |
|---|---|
| ECC plugin structure (`.claude-plugin/plugin.json`) | Task 1 |
| Generic schema.yaml (LangGraph rule removed) | Task 2 |
| Generic tasks.md template (config.yaml references) | Task 3 |
| Generic apply.md (Setup block + config VISUAL DIFF) | Task 4 |
| Generic explore/propose/archive commands | Task 5 |
| Generic remaining templates | Task 6 |
| `bin/opsx-install` schema promotion script | Task 7 |
| `config-template.yaml` for new projects | Task 8 |
| README with install + new project + upgrade guide | Task 9 |
| Push to GitHub | Task 10 |
| python-agent config.yaml — `project:` section | Task 11 |
| python-agent config.yaml — `rules.tasks` LangGraph rule | Task 11 |
| Plugin install + schema promotion verification | Task 12 |
| Delete project-level schema + commands | Task 13 |
| Update openspec-workflow.md distribution section | Task 14 |
