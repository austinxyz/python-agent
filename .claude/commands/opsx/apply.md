---
name: "OPSX: Apply"
description: Execute tasks.md with TDD + review skills wired into the gates
category: Workflow
tags: [workflow, artifacts, experimental]
---

Execute the tasks defined in `openspec/changes/<topic>/tasks.md`. Invoke superpowers skills at the gates the planning phase wired in.

**Input**: Optionally specify a change name (e.g., `/opsx:apply add-auth`). If omitted, infer from conversation context. If ambiguous, run `openspec list --json` and use **AskUserQuestion** to let the user select.

---

**Setup**: Before starting, read `openspec/config.yaml` and note the `project` section:
- `project.dev_stack_command` — command to bring up the dev stack (used in VISUAL DIFF tasks)
- `project.test_commands` — list of test commands (used in verification step)
- `project.e2e_command` — e2e test command (optional)
- `project.custom_verification_checks` — appended to verification-before-completion
- `project.design_system` — design system name (referenced in MOCK tasks for token naming)

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

Convention for the task ordinal `N.X`: `N` is the group number; `X` is the position within the group (1, 2, 3, …). The keyword AFTER `N.X` (RED / GREEN / MOCK / VISUAL DIFF / Run …) decides dispatch — NOT the ordinal letter. The schema's tasks template assigns the last-in-group code-review task position `Z` by convention, but you should match on the "Run superpowers:requesting-code-review" prefix, not on `.Z`.

- **`- [ ] N.X RED — ...`** → write the failing test, run it, confirm the failure mode matches the description (often "function not defined" or "expected X got undefined"). Mark the checkbox.

- **`- [ ] N.X GREEN — ...`** → write the minimal code to pass. Run the test. Confirm pass. Mark the checkbox.

- **`- [ ] N.X MOCK — ...`** → open the mock file at the path shown in the task. Note the design tokens and verbatim text strings called out. Mark the checkbox.

- **`- [ ] N.X VISUAL DIFF — ...`** → bring up the dev stack (`project.dev_stack_command` from `openspec/config.yaml`, or whatever the task says), navigate to the route, eyeball the rendered UI against the mock. Fix any token/color/text drift. Mark the checkbox.

- **`- [ ] N.X Run superpowers:requesting-code-review on the diff for group N — ...`** → invoke `superpowers:requesting-code-review` via the **Skill** tool. Pass the group's diff as input. Address CRITICAL/HIGH findings inline before moving on; MEDIUM/LOW go to a follow-up note in the change directory.

- **Final group's verification task** (`Run superpowers:verification-before-completion`) → invoke `superpowers:verification-before-completion`. Runs pytest / vitest / e2e / `console.log` audit. Fix any failures before marking complete.

Mark each task `- [x]` immediately after completing it (not in a batch at the end).

### 4. On completion or pause: status

Run:

```bash
openspec status --change <name>
```

If all tasks are `- [x]`:

> "Apply complete. Next: ship (e.g. `git push`, plus any project-specific deploy — see CLAUDE.md), then `/opsx:archive <name>`."

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
