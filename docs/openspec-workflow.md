# OpenSpec + Superpowers Workflow 使用指南

> 这是面向**使用者**的指南（你或未来给项目做改动的人）。
> 想看为什么这么设计、架构怎么拆，去 [docs/superpowers/specs/2026-05-10-openspec-superpowers-workflow-design.md](superpowers/specs/2026-05-10-openspec-superpowers-workflow-design.md)。

---

## TL;DR

每个 change 走 4 个 slash command，每个 command 是一个不能跳的 phase：

```
/opsx:explore <topic>   → 谈想法 → 写 requirements.md（DRAFT → REVIEWED）
                            ↓
/opsx:propose <topic>   → 生成 proposal/specs/design/tasks
                            ↓
/opsx:apply <topic>     → 跑 tasks（TDD + 自动 code review）
                            ↓
/opsx:archive <topic>   → 归档 + 更新 capability spec + CLAUDE.md
```

`<topic>` 是 kebab-case 名（`nas-https` / `multi-user-auth-core` 之类），从头跟到底。

---

## 什么时候用，什么时候不用

| 场景 | 用 OpenSpec 吗 |
|---|---|
| 加个新功能 / 改架构 / 加新 view | ✅ 用 |
| 修个 bug | ❌ 不用，直接改 + commit |
| 改个 typo / 文档润色 | ❌ 不用 |
| 重构一个模块 | ✅ 用（够大就用） |
| 试验性脚本 / 一次性脚本 | ❌ 不用 |
| 加一个第三方 service 集成 | ✅ 用 |
| 调一个 env var | ❌ 不用 |
| 改 UI 风格 / 加一个 view | ✅ 用 |

判断标准：**会动到多个文件、需要多轮决策、值得有"为什么这么做"的记录吗？** 是 → 用 OpenSpec。

---

## Phase 1 — `/opsx:explore <topic>`

**目的：** 把脑子里的想法变成一份审过的 requirements 文档。

**输入：** 想法描述。可以模糊（`real-time collaboration`）也可以具体（`auth 系统该重构了`）。

**5 步走，agent 按序推进：**

1. **Free-thinking** — 像聊天一样讨论，agent 一次问一个问题，画 ASCII 图，读你项目的代码理解上下文。不写代码、不写文档、不预判实现。
2. **起草 requirements** — 觉得讨论够清晰了，agent 主动说"我想起草了"，落到 `docs/superpowers/specs/<date>-<topic>-requirements.md`，frontmatter 标 `Status: DRAFT`。
3. **Brainstorming review** — agent 调 `superpowers:brainstorming` 的 self-review checklist 体检 draft：占位符 / 一致性 / scope / 歧义。漏的洞回头补，补完把 `Status: DRAFT → REVIEWED`。
4. **UI 旁路（仅 `HAS_UI_SURFACE: yes` 时）** — 如果有 UI 表面：选 design 风格（`awesome-design-md` 或继承项目现有风格），用 Visual Companion 在浏览器里画 mock，保存到 `docs/superpowers/specs/mocks/<date>-<topic>-mocks.html`。
5. **Commit + handoff** — 提交 requirements（+ 可能的 mocks），告诉你下一步 `/opsx:propose <topic>`。

**手动改成 `REVIEWED` 不行** —— `/opsx:propose` 拒接 `Status: DRAFT` 的 requirements，但它信任 `REVIEWED` 字段；没真正过 review pass 就改 status 等于自欺欺人。

**Anti-pattern：** 中途说"行了直接干吧" → 命令拒绝。phase 边界是硬的。

### 产出文件

- `docs/superpowers/specs/<date>-<topic>-requirements.md`（必有）
- `docs/superpowers/specs/mocks/<date>-<topic>-mocks.html`（仅 UI change）

---

## Phase 2 — `/opsx:propose <topic>`

**目的：** 把 reviewed requirements 转成完整的 OpenSpec change（proposal + spec deltas + design + tasks）。

**前置检查：** `docs/superpowers/specs/<date>-<topic>-requirements.md` 存在 + `Status: REVIEWED`。没满足 → 命令拒绝，让你回 `/opsx:explore`。

**做什么：**

1. `openspec new change <topic> --schema superpowers-driven` 建 change 目录
2. 按依赖顺序生成每个 artifact：
   - `proposal.md` — frontmatter 带 `HAS_UI_SURFACE: yes/no`、Why / What Changes / Capabilities / Impact / Out of Scope
   - `specs/<capability>/spec.md` — 每个新增 / 修改的 capability 一份 SHALL + Scenario delta
   - `design.md` — 决策（含 alternatives）/ 风险 / 迁移计划 / UI Fidelity（UI change 必须）
   - `mocks` 已经在 Phase 1 写完了，这里只是 verify 一下文件存在
   - `tasks.md` — RED/GREEN 配对、MOCK + VISUAL DIFF 三明治（UI 任务）、每个 group 结尾 code-review checkpoint、最后 group 跑 verification-before-completion
3. commit + handoff

**自动注入的 task 模板规则**（schema 的 `tasks` instruction 里）：

- 每个新功能必须有 `N.X RED — <写失败测试>` 紧跟 `N.X+1 GREEN — <最小实现>`
- 每个 group 结尾必有 `N.Z Run superpowers:requesting-code-review on the diff for group N`
- 涉及 view 的任务必有 `MOCK → RED → GREEN → VISUAL DIFF` 三明治
- 最后 group 必有 `Run superpowers:verification-before-completion`

### 产出文件

- `openspec/changes/<topic>/proposal.md`
- `openspec/changes/<topic>/specs/<cap>/spec.md`（一个或多个）
- `openspec/changes/<topic>/design.md`
- `openspec/changes/<topic>/tasks.md`
- `openspec/changes/<topic>/.openspec.yaml`（schema 锁定）

---

## Phase 3 — `/opsx:apply <topic>`

**目的：** 真跑代码 + 自动触发 TDD 和 code review 节点。

**做什么：**

1. 读全部 context（proposal / specs / design / mocks / requirements）
2. **Session start 必调 `superpowers:test-driven-development`** —— 这个 skill 全程守着「没 RED 不许 GREEN」
3. 按 `tasks.md` 顺序逐个 task 执行：
   - `RED` → 写失败测试、跑、确认失败模式
   - `GREEN` → 最小实现、跑、确认通过
   - `MOCK` → 打开 mock 文件对照
   - `VISUAL DIFF` → 起 dev stack、肉眼跟 mock 对、修飘移
   - `Run superpowers:requesting-code-review` → 真调 review skill，CRITICAL/HIGH 当下修
4. 最后 group 调 `superpowers:verification-before-completion`（pytest / vitest / e2e / `console.log` 审）

**每个 task 完成立刻 `- [x]`，不批处理。**

**手动 ops 怎么办：** 有些 task 是浏览器 / shell / 第三方控制台操作（比如 `nas-https` Group 1：注册 Tailscale、装 daemon、建 OAuth client）。agent 会**暂停**告诉你这是你来做的，列清单（参考 `openspec/changes/nas-https/manual-ops.md`），你做完回报给 agent，agent 接着做后面的代码 group。

---

## Phase 4 — `/opsx:archive <topic>`

**目的：** 归档 change 到 `openspec/changes/archive/`，同时做 4 个 cleanup —— bare CLI 不会自动做的。

**做什么：**

1. **Pre-flight：** 确认所有 artifact done、所有 task `[x]`、delta spec 跟 capability spec 同步过
2. `openspec archive <topic>` — change 目录搬到 `openspec/changes/archive/<date>-<topic>/`，spec delta merge 进 `openspec/specs/<capability>/spec.md`
3. **Cleanup 1：填 capability spec 的 `## Purpose`** —— `openspec archive` 留个 `TBD` 占位，要从 proposal 的 Why + requirements 的 Goals 提炼 1-3 句话填上。**这是这个 workflow 存在的主要动机之一** —— `multi-user-auth-core` 当时这条漏了导致 capability spec 长期 `TBD`。
4. **Cleanup 2：更新 `openspec/specs/README.md`** —— 给新 capability 加一条目（用户故事 / 覆盖需求 / 后台 / 前台 / 验收）
5. **Cleanup 3：更新 `CLAUDE.md` Pitfalls** —— 如果这次踩到非显然的坑就加一条；没踩就跳过，不要硬编
6. **Cleanup 4：条件性更新项目根 `README.md`** —— 仅当这次 change 引入用户可见的新功能 / 行为变化时（auth flow 改了 = 要更新；ops 内部 = 跳过）
7. Dev log 检查（`docs/log/<today>.md`），没写就提醒你写
8. 单个 cleanup commit + 输出 "Workflow complete"

---

## 已用 workflow 跑过的 change

| Change | 用什么 schema | 状态 | 备注 |
|---|---|---|---|
| `multi-user-auth-core` | `spec-driven`（旧） | ✅ archived | workflow 的前身练手，发现了 `## Purpose: TBD` 等坑 |
| `multi-user-auth-admin-ui` | `spec-driven`（旧） | in-flight | propose 阶段；继续用旧 schema 到 archive |
| `chat-file-pinning` | （继承 default） | in-flight | 创建早于 schema 切换；archive 时会有遗留问题 |
| `openspec-superpowers-workflow` | 自身 | ✅ archived | 这个 workflow 自身的实施 |
| `nas-https` | `superpowers-driven` | in-flight | 第一个真正用新 workflow 全程跑的 change |

---

## 文件去哪儿了

```
项目根/
├── docs/
│   ├── openspec-workflow.md          ← 你正在看的文件（用户向）
│   └── superpowers/
│       └── specs/
│           ├── 2026-05-10-openspec-superpowers-workflow-design.md   ← workflow 设计文档（架构向）
│           ├── 2026-05-10-openspec-superpowers-workflow.md          ← workflow 概览（一页纸）
│           ├── 2026-05-10-<topic>-requirements.md                   ← 每个 change 的 requirements
│           ├── 2026-05-10-<topic>-design.md                         ← 早期 change 的 design 文档（spec-driven 时代的）
│           └── mocks/
│               └── 2026-05-10-<topic>-mocks.html                    ← UI change 的 mock
│
├── openspec/
│   ├── config.yaml                  ← 项目 context（tech stack、conventions、路径约定）
│   ├── schemas/superpowers-driven/  ← workflow schema（artifact 图 + 模板）
│   │   ├── schema.yaml
│   │   └── templates/{requirements,proposal,specs,design,mocks,tasks}.{md,html}
│   ├── changes/                     ← 在飞的 change
│   │   ├── <topic>/
│   │   │   ├── .openspec.yaml       ← schema 锁定
│   │   │   ├── proposal.md
│   │   │   ├── specs/<cap>/spec.md
│   │   │   ├── design.md
│   │   │   ├── tasks.md
│   │   │   └── manual-ops.md        ← 可选；apply 阶段需要手动 ops 时放这儿
│   │   └── archive/
│   │       └── <date>-<topic>/      ← archived 后搬这儿
│   └── specs/                       ← 真理之源：capability spec
│       ├── README.md
│       ├── multi-user-auth/spec.md
│       └── ...其他 capability
│
├── .claude/commands/opsx/           ← 四个 slash command
│   ├── explore.md
│   ├── propose.md
│   ├── apply.md
│   └── archive.md
│
└── CLAUDE.md                        ← 项目级 pitfall 沉淀（Cleanup 3 写这儿）
```

---

## 已知 gotchas

### 1. `openspec status` 把 `requirements` 和 `mocks` 报成 `[ ]` 即使文件存在

OpenSpec 1.2.0 不替换 `generates:` 里的 `{{date}}` / `{{change}}` 占位符。它检查文件存在性时用的是字面字符串 `<repo>/.../{{date}}-{{change}}-requirements.md`，永远不存在 → 永远报 `[ ]`。

实际文件被 slash command 自己写进了真实路径（替换过占位符的）。

**怎么验证：** `ls docs/superpowers/specs/*-<topic>-requirements.md`、`ls docs/superpowers/specs/mocks/*-<topic>-mocks.html`。

**别误读：** `[ ]` 不代表 missing。

### 2. `Status: REVIEWED` gate 不在 OpenSpec CLI 里强制

OpenSpec CLI 不读 requirements 文件的 frontmatter。**这个 gate 是 `/opsx:propose` 的 slash command 自己检查的**。理论上一个 agent 可以无视 gate 强行往下走，但是 propose 命令显式 refuse 了 DRAFT 输入。trust + observation，不是密码学保证。

### 3. Apply 阶段碰到手动 ops 会自然暂停

`nas-https` 的 Group 1 就是这样的例子 —— 8 个 task 全是浏览器 / NAS shell / Google Cloud Console 操作。agent 会列清单（写到 `openspec/changes/<topic>/manual-ops.md`），暂停等你给值。

### 4. `tailscale serve` / `docker exec` 命令配置不进 git

某些操作环境（Tailscale daemon state、UGOS 系统设置）的产物不在 git 里。这种东西要写进 `manual-ops.md` 或 `CLAUDE.md` 的 NAS 部署部分，让"NAS 重装 / 换机器"时能回放。

### 5. 第一次用 workflow 的 change 比后续慢

`nas-https` 是第一个全程跑的 change。Phase 1 花了 7 轮对话锁定 7 个 pivot 决策。后续 change 对话会更短 —— 模式熟了 / 决策树共享了。

---

## 参考

- **设计文档（为什么这么搭）：** [docs/superpowers/specs/2026-05-10-openspec-superpowers-workflow-design.md](superpowers/specs/2026-05-10-openspec-superpowers-workflow-design.md)
- **一页纸概览：** [docs/superpowers/specs/2026-05-10-openspec-superpowers-workflow.md](superpowers/specs/2026-05-10-openspec-superpowers-workflow.md)
- **实施 plan（这次 rollout 的 12 个 task）：** [docs/superpowers/plans/2026-05-10-openspec-superpowers-workflow.md](superpowers/plans/2026-05-10-openspec-superpowers-workflow.md)
- **Schema 定义：** [openspec/schemas/superpowers-driven/schema.yaml](../openspec/schemas/superpowers-driven/schema.yaml)
- **四个 slash command：** [.claude/commands/opsx/](../.claude/commands/opsx/) 下面的 `explore.md` / `propose.md` / `apply.md` / `archive.md`
- **OpenSpec 上游文档：** [github.com/Fission-AI/OpenSpec/blob/main/docs/customization.md](https://github.com/Fission-AI/OpenSpec/blob/main/docs/customization.md)（schema 字段说明）

---

## 下一个 change 想做什么？

参考 `docs/log/2026-05-10.md` 列的 backlog：

- `nas-https` —— in-flight，Phase 3 卡在 Group 1 手动 ops（你做）
- `multi-user-auth-admin-ui` —— 用网页管理用户、改密、禁用，替代 CLI（spec-driven schema，已 propose）
- `auth-rate-limiting` —— login 端点限流
- `auth-audit-log` —— admin 操作审计
- `nas-funnel` —— Tailscale Funnel，把 `nas-https` 之后的 LAN-only 切到公网
- `cloud-deploy` —— 部署到云（depends on `nas-https`）

任何一个的入口都是 `/opsx:explore <kebab-name>`。
