# Knowledge Agent — 设计规格文档

**日期：2026-05-05 | 项目：python-agent | 状态：已确认**

---

## 1. 项目概述

### 1.1 目标

构建一个通用知识库 Agent：将原始知识消化为结构化条目存入向量数据库，结合用户私有个人数据，通过 RAG 提供专业问答。

首个使用场景：个人理财知识库（迁移并升级现有 `wealth` 项目）。

### 1.2 核心能力

- **知识摄入**：从文件、URL、MCP 数据源（Google Docs、Notion 等）摄入原始知识，原始文件永久保留
- **RAG 问答**：结合公共知识库和用户私有数据，流式生成专业建议
- **私有数据管理**：结构化模板录入个人情况（税务、账户、持仓等），支持私有笔记
- **知识反哺**：将好的 Chat 回答保存为私有笔记或提炼为知识条目

### 1.3 设计原则

- **通用架构，场景优先**：系统不绑定领域，V1 以理财为场景跑通
- **个人优先，多用户预留**：V1 单用户，数据模型已含 `user_id` 字段，扩展时只需加认证层
- **原始文件不丢**：摄入后保留原始文件，可随时查看和重新处理
- **隐私边界清晰**：公共知识库与私有数据物理隔离（Qdrant 不同集合），私有内容不出本机

---

## 2. 技术架构

### 2.1 技术栈

| 层 | 技术 | 说明 |
|---|---|---|
| 前端 | Vue 3 + Vite | SPA，左侧导航布局 |
| 后端 | Python + Flask | REST API + SSE 流式输出 |
| Agent 编排 | LangGraph | 内嵌于 Flask 服务 |
| 向量数据库 | Qdrant | 自托管 Docker，免费开源 |
| LLM（对话） | Claude Haiku / Sonnet | 通过 Anthropic API，可配置切换 |
| Embeddings | OpenAI text-embedding-3-small | 生成向量，~$0.02/百万 token |
| 原始文件存储 | Docker Volume | `/app/uploads/` 持久化挂载 |
| 元数据存储 | SQLite | 文件注册表、笔记元数据 |

### 2.2 Docker Compose 结构

```
services:
  frontend    # Vue 3 + Vite，nginx 静态服务，port 3000
  api         # Flask + LangGraph，port 5000
  qdrant      # 向量数据库，port 6333

volumes:
  qdrant_data  # 向量数据持久化
  uploads      # 原始文件持久化（/app/uploads/）
```

三个服务，两个持久卷。本地开发、NAS、Railway 使用同一份 `docker-compose.yml`，差异仅在 `.env` 环境变量。

### 2.3 LLM 集成

**对话 LLM（可切换）：**

```python
# 环境变量控制，无需改代码
LLM_PROVIDER=anthropic          # 或 openai
LLM_MODEL=claude-haiku-4-5-20251001  # 默认 Haiku，前端可选 Sonnet
ANTHROPIC_API_KEY=sk-ant-...
```

**Embeddings（固定 OpenAI）：**

```python
EMBEDDING_PROVIDER=openai
EMBEDDING_MODEL=text-embedding-3-small
OPENAI_API_KEY=sk-...
```

Anthropic 无自己的 Embedding API，因此 Embedding 使用 OpenAI，两个 key 都需要配置。OpenAI Embedding 是 V1 硬依赖，无降级方案。

### 2.4 迁移路径

```
本地开发  →  docker compose up
NAS       →  同一份 docker-compose.yml，Volume 挂载到 NAS 磁盘
Railway   →  各服务独立部署，Volume 换 Railway 持久存储，Qdrant 换 Qdrant Cloud 免费层
```

---

## 3. LangGraph 设计

### 3.1 Ingest Pipeline（确定性流水线）

原始知识摄入流程，无循环，每步确定性执行：

```
Source Router
    ↓（识别来源：file / url / mcp / text）
Fetch Node
    ↓（PDF解析 · URL抓取 · MCP调用 · 文本接收）
Clean Node
    ↓（去噪、格式统一、语言检测）
Chunk Node
    ↓（目标 512 tokens，50 token overlap；文档不足 512 tokens 则不分块直接作为单块）
Embed Node
    ↓（text-embedding-3-small 生成向量）
    ├→ Store → knowledge 集合（公共知识库）
    └→ Store → private 集合（私有数据）
    ↓
Summary Node
    ↓ 返回给前端：{job_id, chunk_count, file_id, status: "completed"}
```

知识库 vs 私有数据由摄入时用户选择（前端「存入目标」切换）。

### 3.2 Q&A ReAct Agent（工具调用循环）

```
Query Node（接收用户问题，携带对话历史）
    ↓
Agent Node（Claude 决策：需要调哪些工具？）
    ↓ 工具调用
    ├ search_knowledge(query, top_k)   # 搜索公共知识库
    ├ search_private(query, top_k)     # 搜索私有数据（按 user_id 过滤）
    └ get_entry(entry_id)              # 按 ID 获取完整条目
    ↓ 观察结果
    ↺ 循环（上下文不足则继续调工具）
    ↓ 上下文充足
Generate Node（综合知识 + 私有数据，流式 SSE 输出）
    ↓
History Node（保存对话记录，支持多轮连续对话）
```

---

## 4. 数据模型

### 4.1 Qdrant 向量集合

**`knowledge` 集合（公共知识库）**

| 字段 | 类型 | 说明 |
|---|---|---|
| `id` | uuid | 自动生成 |
| `vector` | float[] | 文本 embedding |
| `domain` | string | 如 `finance` |
| `topic` | string | 如 `Roth IRA` |
| `source_file_id` | string | 指向原始文件 |
| `chunk_index` | int | 在原文中的位置 |
| `updated_at` | timestamp | 最近更新时间 |
| `status` | string | `draft` / `stable` / `outdated` |

**`private` 集合（用户私有数据）**

| 字段 | 类型 | 说明 |
|---|---|---|
| `user_id` | string | V1 固定 `default`，多用户扩展点 |
| `topic` | string | 如 `tax_situation` |
| `template_type` | string | `tax` / `retirement` / `portfolio` / `note` / `custom` |
| `source_file_id` | string | 指向原始文件（如有） |
| `updated_at` | timestamp | |

### 4.2 SQLite 元数据库

**`files` 表**（原始文件注册表）

```sql
id          TEXT PRIMARY KEY   -- UUID
user_id     TEXT               -- 文件归属用户
filename    TEXT               -- 存储文件名
orig_name   TEXT               -- 原始文件名
source_type TEXT               -- file / url / mcp
source_url  TEXT               -- URL 来源（如有）
domain      TEXT               -- 归类领域
topic       TEXT               -- 归类主题
size_bytes  INTEGER
chunk_count INTEGER
created_at  TIMESTAMP
```

**`chat_sessions` 表**（对话历史）

```sql
id          TEXT PRIMARY KEY   -- 会话 UUID
user_id     TEXT
title       TEXT               -- 自动取第一条消息前 20 字
created_at  TIMESTAMP
updated_at  TIMESTAMP
```

**`chat_messages` 表**（消息记录）

```sql
id          TEXT PRIMARY KEY
session_id  TEXT               -- FK → chat_sessions.id
role        TEXT               -- user / assistant
content     TEXT
sources     TEXT               -- JSON：引用的条目 ID 列表
model       TEXT               -- 使用的模型
created_at  TIMESTAMP
```

**`notes` 表**（私有笔记元数据）

```sql
id          TEXT PRIMARY KEY
user_id     TEXT
title       TEXT               -- 用户自定义名称
directory   TEXT               -- 目录路径，如 "退休规划/Roth相关"
chat_ref    TEXT               -- 来源 Chat 会话 ID（如有）
content     TEXT               -- 笔记正文（含问答原文）
created_at  TIMESTAMP
updated_at  TIMESTAMP
```

---

## 5. API 路由

### 5.1 摄入 API

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | `/api/ingest` | 摄入文件/URL/文本，参数：`source_type`, `destination`（knowledge/private） |
| POST | `/api/ingest/mcp` | 从 MCP 数据源摄入（Google Docs、Notion） |
| GET | `/api/ingest/status/{job_id}` | 查询摄入进度 |

### 5.2 知识库 API

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/wiki/tree` | 返回知识库树结构（domain → topic） |
| GET | `/api/wiki` | 列出条目，支持 `domain`/`topic` 过滤 |
| GET | `/api/wiki/{id}` | 获取单条条目 |
| DELETE | `/api/wiki/{id}` | 删除条目 |

### 5.3 文件 API

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/files` | 列出已摄入文件，支持树形 |
| GET | `/api/files/{id}` | 查看/下载原始文件 |
| DELETE | `/api/files/{id}` | 删除文件及对应向量 |
| POST | `/api/files/{id}/resync` | 重新摄入（MCP 源同步更新） |

### 5.4 对话 API

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | `/api/chat` | 发起对话，SSE 流式返回，参数：`model`（haiku/sonnet）, `scope`（数组，可同时含 `knowledge`/`private`，两者都选时同时检索） |
| GET | `/api/chat/sessions` | 获取历史会话列表 |
| GET | `/api/chat/sessions/{id}` | 获取会话完整记录 |

### 5.5 私有数据 API

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/private/templates` | 获取可用模板列表 |
| GET | `/api/private/entries` | 列出私有条目（结构化模板） |
| POST | `/api/private/entries` | 新建私有条目 |
| PUT | `/api/private/entries/{id}` | 更新私有条目 |
| DELETE | `/api/private/entries/{id}` | 删除私有条目 |
| GET | `/api/private/notes` | 列出私有笔记（含目录树） |
| POST | `/api/private/notes` | 保存 Chat 回答为私有笔记 |
| PUT | `/api/private/notes/{id}` | 编辑笔记 |

### 5.6 Prompt 库 API

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/prompts` | 获取 Prompt 列表，支持分类过滤 |
| POST | `/api/prompts` | 保存自定义 Prompt |
| POST | `/api/prompts/{id}/favorite` | 收藏/取消收藏 |

---

## 6. 前端页面设计

### 6.1 整体布局

```
┌─────────────────────────────────────────────┐
│  🧠 Knowledge Agent          [当前页面标题]  │
├──────────┬──────────────────────────────────┤
│          │                                  │
│  左侧    │         主内容区                  │
│  导航    │                                  │
│  100px   │                                  │
│          │                                  │
│ 📚 知识库 │                                  │
│ ⬆ 摄入   │                                  │
│ 💬 对话   │                                  │
│ 🔒 私有   │                                  │
└──────────┴──────────────────────────────────┘
```

Vue Router：`/` → redirect `/wiki` | `/wiki` | `/wiki/:id` | `/ingest` | `/chat` | `/private`

---

### 6.2 知识库页面（`/wiki`）

**布局：** 左树 + 右内容（两栏）

```
├── [🔍 搜索框]
├── 树形导航（左侧，160px）
│   └── finance
│       ├── ▾ 账户类型
│       │   ├── 📄 Roth IRA  ← 当前选中
│       │   ├── 📄 401K
│       │   └── 📄 HSA
│       ├── ▾ 税务策略
│       └── ▶ 退休规划
└── 条目内容（右侧）
    ├── 标题 + 分类标签 + 状态
    ├── 正文（含 [[wikilinks]] 可跳转）
    ├── 来源引用
    └── [查看原文] 按钮 → 跳转到对应文件
```

树节点：domain 层（展开/折叠）→ topic 层（展开/折叠）→ entry 条目（叶节点）

---

### 6.3 摄入页面（`/ingest`）

**两个 Tab：**

**Tab 1「➕ 新摄入」：**
- 存入目标切换：`📚 公共知识库` / `🔒 私有数据`
- 文件上传区（拖拽，支持 PDF/MD/TXT/DOCX）
- URL 摄入输入框 + 抓取按钮
- MCP 数据源卡片（Google Docs、Notion，可扩展）
- 摄入进度列表（实时状态 + 分块数量）

**Tab 2「🗂 已摄入文件」：**

布局：左树 + 右文件列表

```
├── 树形导航（左侧，160px）
│   ├── 全部文件 (12)
│   └── finance (10)
│       ├── ▾ 账户类型 (4)  ← 当前选中
│       ├── ▾ 税务策略 (3)
│       └── ▶ 退休规划 (3)
│   └── 🔒 私有 (2)
└── 文件列表（右侧）
    ├── 面包屑：全部 › finance › 账户类型
    ├── [+ 摄入到此分类] 按钮
    └── 文件卡片列表
        ├── 图标区分：📄 文件 / 🔗 URL / 📝 MCP
        ├── 文件名、大小、日期、分块数
        ├── 领域/主题标签
        └── 操作：👁 查看 / ⬇ 下载 / 🔄 同步（MCP）/ 🗑 删除
```

树结构与知识库一致（同一套 domain → topic 层级）。

---

### 6.4 对话页面（`/chat`）

**布局：** 左导航 + 会话列表（150px）+ 对话主区

**会话列表：**
- 「＋ 新对话」按钮
- 历史会话列表（按时间倒序，点击恢复）

**对话主区工具栏：**
- 模型切换：`⚡ Haiku`（默认） / `🧠 Sonnet`
- 范围开关：`📚 知识库` / `🔒 私有`（独立开关）
- `📚 Prompt 库` 按钮

**消息区：**
- 用户消息（右对齐，蓝色气泡）
- AI 消息（左对齐，含检索过程可见提示）
- 每条 AI 消息底部：
  - 来源引用（绿色 = 知识库，紫色 = 私有数据）
  - 操作行：👍 有用 / 📋 复制 / ⭐ 保存回答 / 🔄 重新生成

**空状态：** 展示 6 张推荐 Prompt 卡片（按领域分类，点击填入输入框）

**保存回答流程：**
1. 点「⭐ 保存回答」→ 弹出保存对话框
2. 输入笔记名称（如「2026 Roth 转换决策分析」）
3. 树形目录选择器（选择私有笔记目录，可新建文件夹）
4. 预览保存内容
5. 保存 → 存入私有区域

**Prompt 库：**
- 分类：投资规划 / 账户管理 / 税务策略 / 退休规划 / 跨境合规 / 知识解释 / ⭐ 我收藏的
- 每条 Prompt 标注：「需要私有数据」或「仅知识库」
- 支持收藏、使用、自定义新增

---

### 6.5 私有数据页面（`/private`）

**两种内容类型共用一个页面：**

**结构化模板条目（上方列表）：**

预设模板：
- 💰 税务情况（申报状态、税档、AGI、FBAR/FATCA）
- 🏦 退休账户（401K、Roth IRA、Traditional IRA）
- 📈 投资持仓（券商、主要持仓及成本）
- 👤 个人基本情况（收入、家庭、目标）
- 🏠 房产资产（房产、贷款、净值）
- ✏️ 自由格式（Markdown）

新建流程：「+ 新建条目」→ 选模板 → 填写结构化表单 → 保存

**私有笔记（树形结构）：**
- 树形目录（用户自定义，如「退休规划/Roth 相关」）
- 来源于 Chat 保存，或手动新建
- 每条笔记显示创建时间、来源会话
- 操作：✏️ 编辑 / 💬 在 Chat 中继续

---

## 7. MCP 数据源集成

MCP 作为**知识摄入来源**（不是 UI），通过 LangGraph Ingest Pipeline 的 Fetch Node 调用：

**V1 支持：**
- Google Docs（读取文档内容）
- Notion（读取页面内容）

**MCP 凭证配置（`.env`）：**
```
GOOGLE_DOCS_MCP_TOKEN=...
NOTION_MCP_TOKEN=...
```

**扩展方式：** 在 Fetch Node 中注册新的 MCP Client，前端「MCP 数据源」卡片对应添加入口。

---

## 8. 私有数据隔离机制

Qdrant 查询时通过 payload 过滤实现隔离：

```python
# 查询私有数据时自动附加 user_id 过滤
results = qdrant_client.search(
    collection_name="private",
    query_vector=embedding,
    query_filter=Filter(
        must=[FieldCondition(key="user_id", match=MatchValue(value=current_user_id))]
    )
)
```

V1：`user_id = "default"`
多用户扩展：加登录层，从 JWT token 解析 `user_id`，数据层不需要改动。

文件存储隔离：`/app/uploads/{user_id}/{file_id}/`

---

## 9. 理财领域预置内容

### 9.1 知识库初始化（迁移自 `wealth` 项目）

迁移现有 `wiki/` 目录内容：

| domain | topic |
|---|---|
| finance | 账户类型（Roth IRA、401K、HSA、Betterment、SGOV）|
| finance | 税务策略（税损收割、Wash Sale Rule）|
| finance | 投资品种（ETF总览、杠杆ETF、IUL）|
| finance | 退休规划（三段式退休框架、年金）|
| finance | 中美对比（双边资产策略）|

### 9.2 私有数据模板（理财领域）

预置 5 个结构化模板字段（见 6.5 节）。

### 9.3 Prompt 库初始预置（理财领域）

| 类别 | Prompt |
|---|---|
| 投资规划 | 今年我适合做 Roth 转换吗？结合我的税档和 AGI，给出建议转换额度和执行时机。 |
| 投资规划 | 分析我当前持仓的集中度风险，给出再平衡建议。 |
| 税务策略 | 检查我的持仓，找出税损收割机会，注意 Wash Sale Rule。 |
| 税务策略 | 今年年底前有哪些税务操作需要完成？ |
| 退休规划 | 根据我的储蓄和目标退休年龄，评估退休规划进度。 |
| 退休规划 | 我的 401K 配置和雇主匹配策略是否最优？ |
| 账户管理 | 我应该优先填满哪些账户？（401K / Roth IRA / HSA / 应税账户） |
| 跨境合规 | 今年我需要提交 FBAR 吗？有什么需要注意的截止日期？ |
| 知识解释 | 用简单语言解释 [概念]，包括定义、核心规则、常见误区。 |

---

## 10. 项目目录结构

```
python-agent/
├── docker-compose.yml
├── .env.example
├── CLAUDE.md
│
├── backend/                    # Flask API + LangGraph
│   ├── app/
│   │   ├── __init__.py         # Flask app factory
│   │   ├── routes/
│   │   │   ├── ingest.py
│   │   │   ├── wiki.py
│   │   │   ├── chat.py
│   │   │   ├── private.py
│   │   │   ├── files.py
│   │   │   └── prompts.py
│   │   ├── agents/
│   │   │   ├── ingest_pipeline.py   # LangGraph Ingest Graph
│   │   │   └── qa_agent.py          # LangGraph Q&A ReAct Agent
│   │   ├── services/
│   │   │   ├── qdrant_service.py
│   │   │   ├── file_service.py
│   │   │   └── llm_service.py
│   │   └── models/
│   │       └── database.py          # SQLite models
│   ├── uploads/                     # 原始文件（Volume 挂载点）
│   ├── requirements.txt
│   └── Dockerfile
│
├── frontend/                   # Vue 3 + Vite
│   ├── src/
│   │   ├── views/
│   │   │   ├── WikiView.vue
│   │   │   ├── IngestView.vue
│   │   │   ├── ChatView.vue
│   │   │   └── PrivateView.vue
│   │   ├── components/
│   │   │   ├── TreeNav.vue          # 通用树形导航组件
│   │   │   ├── ChatMessage.vue
│   │   │   ├── PromptLibrary.vue
│   │   │   └── SaveNoteModal.vue
│   │   └── router/index.js
│   ├── package.json
│   └── Dockerfile
│
└── docs/
    └── superpowers/
        └── specs/
            └── 2026-05-05-knowledge-agent-design.md
```
