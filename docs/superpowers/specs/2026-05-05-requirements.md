# Knowledge Agent — 需求概要文档

**日期：2026-05-05 | 项目：python-agent | 版本：v1.0**

---

## 编号规则

| 前缀 | 模块 |
|---|---|
| `ARCH` | 基础架构与部署 |
| `DATA` | 数据模型 |
| `ING` | 知识摄入 |
| `KB` | 知识库管理 |
| `CHAT` | 对话与问答 |
| `PRI` | 私有数据管理 |
| `UI` | 前端界面 |

优先级：**P1** 核心功能（MVP）· **P2** 重要功能 · **P3** 增强功能

---

## ARCH — 基础架构与部署

| 编号 | 需求描述 | 优先级 |
|---|---|---|
| ARCH-01 | 使用 Docker Compose 编排三个服务：`frontend`（Vue 3，port 3000）、`api`（Flask，port 5000）、`qdrant`（port 6333） | P1 |
| ARCH-02 | 配置两个持久化 Volume：`qdrant_data`（向量数据）和 `uploads`（原始文件，挂载至 `/app/uploads/`） | P1 |
| ARCH-03 | 所有配置通过 `.env` 文件注入，提供 `.env.example` 模板，不硬编码任何 key 或路径 | P1 |
| ARCH-04 | LLM provider 可通过环境变量切换（`LLM_PROVIDER=anthropic` 或 `openai`），默认使用 Claude Haiku | P1 |
| ARCH-05 | Embedding 使用 OpenAI `text-embedding-3-small`，为 V1 硬依赖 | P1 |
| ARCH-06 | 本地开发、NAS、Railway 使用同一份 `docker-compose.yml`，环境差异仅在 `.env` | P2 |
| ARCH-07 | 私有数据查询必须附加 `user_id` payload 过滤，V1 固定 `default`，为多用户扩展预留接口 | P1 |

---

## DATA — 数据模型

| 编号 | 需求描述 | 优先级 |
|---|---|---|
| DATA-01 | Qdrant `knowledge` 集合存储公共知识库，payload 含：`domain`、`topic`、`source_file_id`、`chunk_index`、`updated_at`、`status` | P1 |
| DATA-02 | Qdrant `private` 集合存储用户私有数据，payload 必须含 `user_id`，额外含：`topic`、`template_type`、`source_file_id`、`updated_at` | P1 |
| DATA-03 | SQLite `files` 表记录文件元数据：`id`、`user_id`、`filename`、`orig_name`、`source_type`、`source_url`、`domain`、`topic`、`size_bytes`、`chunk_count`、`created_at` | P1 |
| DATA-04 | SQLite `chat_sessions` 表记录会话：`id`、`user_id`、`title`（自动取首条消息前 20 字）、`created_at`、`updated_at` | P1 |
| DATA-05 | SQLite `chat_messages` 表记录消息：`id`、`session_id`、`role`（user/assistant）、`content`、`sources`（JSON 引用 ID 列表）、`model`、`created_at` | P1 |
| DATA-06 | SQLite `notes` 表记录私有笔记：`id`、`user_id`、`title`、`directory`（如 `退休规划/Roth相关`）、`chat_ref`、`content`、`created_at`、`updated_at` | P1 |
| DATA-07 | 原始文件存储路径格式：`/app/uploads/{user_id}/{file_id}/`，按用户隔离 | P1 |
| DATA-08 | Chunk 目标大小 512 tokens，overlap 50 tokens；文档不足 512 tokens 时作为单块处理，不分割 | P1 |

---

## ING — 知识摄入

| 编号 | 需求描述 | 优先级 |
|---|---|---|
| ING-01 | 实现 LangGraph Ingest Pipeline，节点顺序：Source Router → Fetch → Clean → Chunk → Embed → Store → Summary | P1 |
| ING-02 | Source Router 支持四种来源类型：`file`（文件上传）、`url`（URL 抓取）、`mcp`（MCP 数据源）、`text`（直接文本） | P1 |
| ING-03 | Fetch Node 支持：PDF 解析、Markdown/TXT 读取、URL 网页抓取、MCP Client 调用 | P1 |
| ING-04 | 摄入时用户选择存入目标：`knowledge`（公共知识库）或 `private`（私有数据） | P1 |
| ING-05 | 原始文件在摄入后永久保留，存入 `/app/uploads/{user_id}/{file_id}/`，SQLite `files` 表记录元数据 | P1 |
| ING-06 | Summary Node 返回标准结果给前端：`{job_id, chunk_count, file_id, status: "completed"}` | P1 |
| ING-07 | V1 支持两个 MCP 数据源：Google Docs 和 Notion，凭证通过 `GOOGLE_DOCS_MCP_TOKEN` / `NOTION_MCP_TOKEN` 配置 | P2 |
| ING-08 | MCP 来源的文件支持「重新同步」操作，重新拉取最新内容并覆盖旧 chunk | P2 |
| ING-09 | `POST /api/ingest` 接受参数：`source_type`、`destination`、文件/URL/文本内容，返回 `job_id` | P1 |
| ING-10 | `GET /api/ingest/status/{job_id}` 返回摄入进度，前端轮询显示实时状态 | P1 |

---

## KB — 知识库管理

| 编号 | 需求描述 | 优先级 |
|---|---|---|
| KB-01 | `GET /api/wiki/tree` 返回知识库树结构（domain → topic → entry 三层） | P1 |
| KB-02 | `GET /api/wiki` 支持按 `domain`、`topic` 过滤，返回条目列表 | P1 |
| KB-03 | `GET /api/wiki/{id}` 返回单条完整条目，含 `source_file_id` 字段以关联原始文件 | P1 |
| KB-04 | `DELETE /api/wiki/{id}` 删除条目及对应 Qdrant 向量 | P2 |
| KB-05 | `GET /api/files` 返回文件列表，支持按 `domain`、`topic`、`user_id` 过滤 | P1 |
| KB-06 | `GET /api/files/{id}` 提供原始文件查看和下载 | P1 |
| KB-07 | `DELETE /api/files/{id}` 删除文件及所有关联向量 chunk | P2 |
| KB-08 | `POST /api/files/{id}/resync` 重新摄入（MCP 源同步更新） | P2 |

---

## CHAT — 对话与问答

| 编号 | 需求描述 | 优先级 |
|---|---|---|
| CHAT-01 | 实现 LangGraph Q&A ReAct Agent，节点：Query → Agent（LLM）→ Tools → Generate → History | P1 |
| CHAT-02 | Agent 可用工具三个：`search_knowledge`（搜索公共知识库）、`search_private`（按 user_id 过滤搜索私有数据）、`get_entry`（按 ID 获取完整条目） | P1 |
| CHAT-03 | `POST /api/chat` 支持参数：`session_id`（续接历史）、`message`、`model`（haiku/sonnet）、`scope`（数组，可同时含 `knowledge` 和/或 `private`） | P1 |
| CHAT-04 | Chat 接口使用 SSE（Server-Sent Events）流式返回，前端实时显示生成内容 | P1 |
| CHAT-05 | AI 回答包含来源引用列表，每个来源含：条目 ID、条目标题、来源类型（knowledge/private） | P1 |
| CHAT-06 | 对话历史持久化至 SQLite `chat_sessions` + `chat_messages` 表，支持多轮连续对话 | P1 |
| CHAT-07 | `GET /api/chat/sessions` 返回历史会话列表（倒序），`GET /api/chat/sessions/{id}` 返回完整记录 | P1 |
| CHAT-08 | `POST /api/prompts` 支持新增自定义 Prompt，`GET /api/prompts` 支持按分类过滤 | P2 |
| CHAT-09 | `POST /api/prompts/{id}/favorite` 收藏/取消收藏 Prompt | P2 |
| CHAT-10 | `POST /api/private/notes` 保存 Chat 回答为私有笔记，参数：`title`（用户自定义）、`directory`（目录路径）、`chat_ref`（会话 ID）、`content` | P1 |

---

## PRI — 私有数据管理

| 编号 | 需求描述 | 优先级 |
|---|---|---|
| PRI-01 | `GET /api/private/templates` 返回可用模板列表，V1 预置 5 个：税务情况、退休账户、投资持仓、个人基本情况、房产资产，另含自由格式 | P1 |
| PRI-02 | `POST /api/private/entries` 根据模板创建结构化私有条目，内容存入 Qdrant `private` 集合，附加 `user_id` | P1 |
| PRI-03 | `PUT /api/private/entries/{id}` 更新私有条目，重新生成 embedding 并更新 Qdrant | P1 |
| PRI-04 | `DELETE /api/private/entries/{id}` 删除私有条目及对应向量 | P2 |
| PRI-05 | `GET /api/private/notes` 返回私有笔记列表，支持目录树结构 | P1 |
| PRI-06 | `PUT /api/private/notes/{id}` 支持编辑笔记内容和重命名/移动目录 | P2 |
| PRI-07 | 私有笔记目录支持用户自定义创建，目录路径以字符串存储（如 `退休规划/Roth相关`） | P1 |

---

## UI — 前端界面

### 通用

| 编号 | 需求描述 | 优先级 |
|---|---|---|
| UI-01 | 应用整体采用左侧固定导航（100px）+ 主内容区布局，四个导航项：📚 知识库 / ⬆ 摄入 / 💬 对话 / 🔒 私有 | P1 |
| UI-02 | 实现通用 `TreeNav.vue` 组件，支持展开/折叠、当前选中高亮、节点数量显示，供知识库和文件管理共用 | P1 |

### 知识库页面（`/wiki`）

| 编号 | 需求描述 | 优先级 |
|---|---|---|
| UI-03 | 知识库采用左树（domain → topic → entry）+ 右内容两栏布局 | P1 |
| UI-04 | 树顶部有搜索框，实时过滤树节点 | P1 |
| UI-05 | 右侧内容区展示条目正文、分类标签、更新时间、status 标记 | P1 |
| UI-06 | 条目内容中的 wikilinks（`[[条目名]]`）可点击跳转到对应条目 | P2 |
| UI-07 | 条目底部显示「查看原文」按钮，跳转到来源文件的查看/下载页 | P1 |

### 摄入页面（`/ingest`）

| 编号 | 需求描述 | 优先级 |
|---|---|---|
| UI-08 | 摄入页面分两个 Tab：「➕ 新摄入」和「🗂 已摄入文件」 | P1 |
| UI-09 | 新摄入 Tab 顶部有「存入目标」切换：公共知识库 / 私有数据 | P1 |
| UI-10 | 新摄入 Tab 支持三种摄入方式：文件拖拽上传、URL 输入、MCP 数据源卡片 | P1 |
| UI-11 | 新摄入 Tab 底部显示实时进度列表，展示文件名、处理状态、分块数量 | P1 |
| UI-12 | 已摄入文件 Tab 采用左树（与知识库相同的 domain → topic 层级）+ 右文件列表两栏布局 | P1 |
| UI-13 | 文件列表每项显示：图标（区分 📄 文件 / 🔗 URL / 📝 MCP）、文件名、大小、日期、分块数、领域标签 | P1 |
| UI-14 | 文件操作按钮：👁 查看（原文）/ ⬇ 下载 / 🔄 重新同步（MCP 来源）/ 🗑 删除 | P1 |
| UI-15 | 文件列表右上角有「+ 摄入到此分类」按钮，点击跳转新摄入 Tab 并预填当前分类 | P2 |

### 对话页面（`/chat`）

| 编号 | 需求描述 | 优先级 |
|---|---|---|
| UI-16 | Chat 布局：左侧会话列表（150px）+ 对话主区，会话列表含「＋ 新对话」按钮和历史列表 | P1 |
| UI-17 | 对话工具栏：模型切换（Haiku/Sonnet）、范围开关（知识库/私有，可独立开关）、Prompt 库入口 | P1 |
| UI-18 | Chat 空状态展示 6 张推荐 Prompt 卡片（按领域分类），点击卡片自动填入输入框 | P2 |
| UI-19 | Prompt 库弹窗支持：按分类浏览、搜索、收藏、使用、自定义新增 | P2 |
| UI-20 | 每条 AI 回答底部显示来源引用（绿色 = 知识库，紫色 = 私有数据），可点击跳转 | P1 |
| UI-21 | AI 回答流式输出，展示生成光标动效；检索过程可见（显示「正在检索...」和查询内容） | P1 |
| UI-22 | 每条 AI 回答底部有操作行：👍 有用 / 📋 复制 / ⭐ 保存回答 / 🔄 重新生成 | P1 |
| UI-23 | 「保存回答」弹窗：输入笔记名称、树形目录选择器（支持新建文件夹）、内容预览、确认保存 | P1 |

### 私有数据页面（`/private`）

| 编号 | 需求描述 | 优先级 |
|---|---|---|
| UI-24 | 私有数据页面分两个区域：结构化模板条目列表（上）和私有笔记树形列表（下） | P1 |
| UI-25 | 新建结构化条目流程：选模板 → 填写表单（含下拉选择、输入框、备注）→ 保存 | P1 |
| UI-26 | 私有笔记以树形目录展示，点击节点显示笔记内容，操作：✏️ 编辑 / 💬 在 Chat 中继续 | P1 |

---

## 需求统计

| 模块 | P1 | P2 | P3 | 合计 |
|---|---|---|---|---|
| ARCH | 5 | 2 | 0 | 7 |
| DATA | 8 | 0 | 0 | 8 |
| ING | 6 | 4 | 0 | 10 |
| KB | 3 | 5 | 0 | 8 |
| CHAT | 8 | 2 | 0 | 10 |
| PRI | 5 | 2 | 0 | 7 |
| UI | 16 | 8 | 0 | 24 |
| **合计** | **51** | **23** | **0** | **74** |

---

*详细架构设计参见：`docs/superpowers/specs/2026-05-05-knowledge-agent-design.md`*
