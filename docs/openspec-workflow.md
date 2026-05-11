# OpenSpec + Superpowers Workflow — python-agent

> **通用 workflow 说明（4 个 phase、何时用、文件结构、gotchas、upstream tracking）移到了 plugin：**
> [`opsx-superpowers/docs/workflow.md`](https://github.com/austinxyz/opsx-superpowers/blob/main/docs/workflow.md)
>
> 这个文件只记录 **本项目专属** 的内容。

![OpenSpec + Superpowers Workflow 全景图](openspec+superpowers.png)

---

## 安装 / 升级 plugin

```bash
# 安装或升级 plugin
claude --plugin-url https://github.com/austinxyz/opsx-superpowers

# Windows：在 Claude Code 提示符里用 ! 前缀（避开 WSL 路由问题）
! bash /c/Users/lorra/projects/opsx-superpowers/bin/opsx-install

# Mac / Linux / Git Bash：
opsx-install

# 验证
openspec schemas   # 应该列出 superpowers-driven（Source: user）
```

---

## 新项目初始化

```bash
cd my-project
openspec init
cp /c/Users/lorra/projects/opsx-superpowers/config-template.yaml openspec/config.yaml
# 编辑 openspec/config.yaml：填 project 节和 context
```

最小 `openspec/config.yaml`：

```yaml
schema: superpowers-driven

project:
  dev_stack_command: "npm run dev:up"
  test_commands:
    - "pytest"
    - "cd frontend && npx vitest run"
  e2e_command: "cd frontend && npm run e2e"
  design_system: "notion"

context: |
  # 你的项目描述
```

---

## 本项目的 change 记录

| Change | Schema | 状态 | 备注 |
|---|---|---|---|
| `multi-user-auth-core` | `spec-driven`（旧） | ✅ archived | workflow 前身练手；发现 `## Purpose: TBD` 坑 |
| `multi-user-auth-admin-ui` | `spec-driven`（旧） | in-flight | propose 阶段；继续用旧 schema 到 archive |
| `chat-file-pinning` | default（旧） | in-flight | 创建早于 schema 切换；archive 时会有遗留 |
| `openspec-superpowers-workflow` | 自身 | ✅ archived | workflow 自身的实施 |
| `nas-https` | `superpowers-driven` | in-flight | 第一个全程用新 workflow 跑的；Phase 3 Group 1 手动 ops 待你来做 |

---

## Backlog

任何一个入口都是 `/opsx:explore <kebab-name>`：

- `nas-https` —— **in-flight**，Phase 3 卡在 Group 1 手动 ops（你来做）
- `multi-user-auth-admin-ui` —— 网页管理用户 / 改密 / 禁用，替代 CLI（已 propose）
- `auth-rate-limiting` —— login 端点限流
- `auth-audit-log` —— admin 操作审计
- `nas-funnel` —— Tailscale Funnel，把 `nas-https` 后的 LAN-only 切到公网
- `cloud-deploy` —— 部署到云（depends on `nas-https`）

---

## 本项目特有 gotchas

> 通用 gotchas（`openspec status` 报 `[ ]`、gate 机制、手动 ops 暂停等）见 plugin 文档。

### 1. `openspec status` 假报 `[ ]`（本项目视角）

在本项目验证：`ls docs/superpowers/specs/*-<topic>-requirements.md`。
详细解释见 [plugin 文档](https://github.com/austinxyz/opsx-superpowers/blob/main/docs/workflow.md#1-openspec-status-shows-requirements-and-mocks-as---even-when-the-files-exist)。

### 2. `nas-https` Group 1 是纯手动 ops

8 个 task 全是浏览器 / UGOS shell / Google Cloud Console。apply 阶段 agent 会暂停，把清单写到 `openspec/changes/nas-https/manual-ops.md`，等你做完回报。

---

## 参考

- **Plugin + workflow 文档：** [opsx-superpowers](https://github.com/austinxyz/opsx-superpowers)
- **Workflow 详细说明：** [opsx-superpowers/docs/workflow.md](https://github.com/austinxyz/opsx-superpowers/blob/main/docs/workflow.md)
- **设计文档（为什么这么搭）：** [docs/superpowers/specs/2026-05-10-openspec-superpowers-workflow-design.md](superpowers/specs/2026-05-10-openspec-superpowers-workflow-design.md)
- **Schema 定义：** [openspec/schemas/superpowers-driven/schema.yaml](../openspec/schemas/superpowers-driven/schema.yaml)（本地 fork，仅本项目）
- **四个 slash command：** [.claude/commands/opsx/](../.claude/commands/opsx/)
- **OpenSpec 上游文档：** [github.com/Fission-AI/OpenSpec](https://github.com/Fission-AI/OpenSpec/blob/main/docs/customization.md)
