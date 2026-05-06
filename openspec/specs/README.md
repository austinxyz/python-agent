# OpenSpec Capabilities

> 所有需求变更通过 OpenSpec 工作流管理。
> 每个 capability 是端到端的可交付用户功能，前后台需求合并在一起。
> 每个 capability spec 是可测试的 BDD 行为规范（SHALL + Scenario）。
>
> **查看方式**：
> - CLI：`openspec show <capability-name>`
> - 文件：`openspec/specs/<capability>/spec.md`
>
> **需求来源**：`docs/superpowers/specs/2026-05-05-requirements.md`
> **架构设计**：`docs/superpowers/specs/2026-05-05-knowledge-agent-design.md`

---

## 交付顺序

```
① foundation  →  ② ingest  →  ③ knowledge-browse  →  ④ private-data  →  ⑤ chat-qa
```

每个阶段完成后均可独立验收：启动应用，走一遍完整的用户路径。

---

## Capabilities

### `foundation`
**用户故事**：应用可以启动，用户能打开浏览器看到基础界面，四个导航页可以切换。

**覆盖需求**：ARCH-01 ~ ARCH-07 · DATA-01 ~ DATA-08 · UI-01 ~ UI-02

**后台**：
- Docker Compose 三服务编排（frontend:3000 · api:5000 · qdrant:6333），含持久化 Volume
- 初始化 Qdrant `knowledge` + `private` 两个集合（payload 结构、索引配置）
- 初始化 SQLite schema（files · chat_sessions · chat_messages · notes 四张表）
- Flask app factory + Blueprint 路由骨架（/api/wiki · /api/ingest · /api/chat · /api/private）
- 环境变量加载（`.env` + `.env.example`），LLM/Embedding provider 切换逻辑
- `GET /api/health` 健康检查，返回 LLM provider 名称 + Qdrant 连通状态

**前台**：
- Vue 3 SPA 骨架（Vite + Pinia + Vue Router），左侧 100px 固定导航 + 主内容区布局
- 四个路由：`/wiki` · `/ingest` · `/chat` · `/private`，每页占位内容
- 通用 `TreeNav.vue` 组件（展开/折叠、选中高亮、节点数量徽章）
- 全局暗色主题（背景 #0a1520，边框 #1e2d3d，强调色 #60a5fa）

**验收标准**：`docker compose up` 后访问 `localhost:3000`，四个导航页切换正常，`/api/health` 返回 200。

---

### `ingest`
**用户故事**：用户可以上传文件（或输入 URL / 粘贴文本），选择存入公共知识库或私有区域，系统完成摄入并显示进度；用户可以在「已摄入文件」Tab 中查看、下载、删除原始文件。

**覆盖需求**：ING-01 ~ ING-06 · ING-09 ~ ING-10 · KB-05 ~ KB-06 · (P2) ING-07 ~ ING-08 · KB-07 ~ KB-08 · UI-08 ~ UI-15

**后台**：
- LangGraph Ingest Pipeline：Source Router → Fetch → Clean → Chunk → Embed → Store → Summary
- Source Router 支持 `file` / `url` / `text` 三种来源（V1）
- Fetch Node：PDF 解析（pdfplumber）、Markdown/TXT 读取、URL 抓取（requests + BeautifulSoup）
- Chunk：目标 512 tokens / overlap 50 tokens，不足 512 tokens 作单块处理
- Embed：OpenAI `text-embedding-3-small`；Store：写入目标 Qdrant 集合（knowledge 或 private）
- 原始文件存 `/app/uploads/{user_id}/{file_id}/`，SQLite `files` 表记录元数据
- Summary Node 返回 `{job_id, chunk_count, file_id, status: "completed"}`
- `POST /api/ingest`（接受 source_type · destination · 文件/URL/文本）返回 `job_id`
- `GET /api/ingest/status/{job_id}` 摄入进度查询（前端轮询）
- `GET /api/files` 文件列表（支持 domain / topic / user_id 过滤）
- `GET /api/files/{id}` 文件查看/下载
- (P2) MCP 数据源（Google Docs / Notion）+ `POST /api/files/{id}/resync`

**前台**：
- 摄入页面（`/ingest`）两个 Tab：「➕ 新摄入」和「🗂 已摄入文件」
- 新摄入 Tab：存入目标切换（公共知识库 / 私有数据）+ 文件拖拽/URL输入/文本粘贴 + 实时进度列表
- 已摄入文件 Tab：左树（domain → topic，复用 TreeNav.vue）+ 右文件列表
- 文件项：类型图标（📄/🔗/📝）· 文件名 · 大小 · 日期 · 分块数 · 领域标签
- 文件操作按钮：👁 查看 / ⬇ 下载 / 🗑 删除；(P2) 🔄 重新同步（MCP 来源）
- (P2) 「+ 摄入到此分类」按钮

**验收标准**：上传一个 PDF → 选择「公共知识库」→ 等待进度显示完成 → 在「已摄入文件」Tab 中能看到该文件并能下载原文。

---

### `knowledge-browse`
**用户故事**：用户可以在知识库页面用树形导航浏览所有摄入的知识条目，搜索内容，查看完整条目，并从条目跳转到原始文件。

**覆盖需求**：KB-01 ~ KB-03 · (P2) KB-04 · UI-03 ~ UI-05 · UI-07 · (P2) UI-06

**后台**：
- `GET /api/wiki/tree` 返回三层树结构（domain → topic → entry，含各层节点数）
- `GET /api/wiki` 支持 `domain` / `topic` 过滤，返回条目列表
- `GET /api/wiki/{id}` 返回完整条目，含 `source_file_id`（关联原始文件）
- (P2) `DELETE /api/wiki/{id}` 删除条目及对应 Qdrant 向量

**前台**：
- 知识库页面（`/wiki`）：左树（复用 TreeNav.vue）+ 右内容两栏布局
- 树顶部搜索框，实时过滤树节点
- 右侧条目内容：正文 · 分类标签 · 更新时间 · status 标记
- 条目底部「查看原文」按钮，跳转至对应文件
- (P2) wikilinks `[[条目名]]` 可点击跳转

**验收标准**：在知识库页面能看到已摄入文件的条目树形结构，点击条目能看到内容，点击「查看原文」能下载原始文件。

---

### `private-data`
**用户故事**：用户可以通过预置模板输入个人财务信息（税务、退休账户、持仓等），也可以查看、编辑已有的私有条目和私有笔记（笔记由 Chat 保存，此阶段实现展示和编辑）。

**覆盖需求**：PRI-01 ~ PRI-05 · PRI-07 · (P2) PRI-04 · PRI-06 · UI-24 ~ UI-26

**后台**：
- `GET /api/private/templates` 返回 V1 预置 5 个模板 + 自由格式：
  税务情况 · 退休账户 · 投资持仓 · 个人基本情况 · 房产资产
- `POST /api/private/entries` 根据模板创建结构化条目，写入 Qdrant `private` 集合，附加 `user_id="default"`
- `PUT /api/private/entries/{id}` 更新条目，重新生成 embedding 并更新 Qdrant
- `GET /api/private/notes` 返回私有笔记列表，支持目录树结构
- (P2) `DELETE /api/private/entries/{id}` 删除条目及向量
- (P2) `PUT /api/private/notes/{id}` 编辑笔记内容 / 重命名 / 移动目录

**前台**：
- 私有数据页面（`/private`）：上区结构化条目列表 + 下区私有笔记树形列表
- 新建条目流程：选模板 → 填写表单（下拉选择 · 输入框 · 备注）→ 保存
- 私有笔记以树形目录展示，点击节点显示笔记内容
- 笔记操作：✏️ 编辑 / 💬 在 Chat 中继续

**验收标准**：选择「税务情况」模板，填写表单并保存 → 在列表中能看到该条目；笔记区展示已有笔记（可为空）。

---

### `chat-qa`
**用户故事**：用户可以基于知识库和私有数据进行多轮对话，AI 回答实时流式输出并显示来源引用；用户可以把好的回答保存为私有笔记（自定义名称 + 目录）；历史会话可以继续。

**覆盖需求**：CHAT-01 ~ CHAT-10 · UI-16 ~ UI-23 · (P2) UI-18 ~ UI-19

**后台**：
- LangGraph Q&A ReAct Agent：Query → Agent（LLM）→ Tools → Generate → History
- 三个工具：`search_knowledge` · `search_private`（必须附加 `user_id` 过滤）· `get_entry`
- `POST /api/chat`：支持 `session_id`（续接）· `message` · `model`（haiku/sonnet）· `scope`（数组，knowledge 和/或 private）
- SSE 流式返回：`{"type":"token","content":"..."}` 逐 token；终止事件 `{"type":"done","sources":[...]}`
- 来源引用：每个来源含条目 ID · 条目标题 · 来源类型（knowledge/private）
- 对话历史持久化：`chat_sessions`（title 取首条消息前 20 字）+ `chat_messages`（含 sources JSON）
- `GET /api/chat/sessions` 历史会话列表（倒序）
- `GET /api/chat/sessions/{id}` 完整会话记录
- `POST /api/private/notes` 保存回答为私有笔记（title · directory · chat_ref · content）
- (P2) `GET /api/prompts` · `POST /api/prompts` · `POST /api/prompts/{id}/favorite`

**前台**：
- Chat 页面（`/chat`）：左侧会话列表（150px）+「＋ 新对话」+ 对话主区
- 工具栏：模型切换（Haiku/Sonnet）· 范围开关（知识库/私有，可独立开关）· Prompt 库入口
- AI 回答流式输出 + 检索过程可见（「正在检索...」+ 查询内容）
- 每条回答：来源引用芯片（绿 = 知识库，紫 = 私有，可点击跳转）
- 回答操作行：👍 有用 / 📋 复制 / ⭐ 保存回答 / 🔄 重新生成
- 「保存回答」弹窗：笔记名称输入 + 树形目录选择器（支持新建文件夹）+ 内容预览 + 确认保存
- (P2) 空状态 6 张推荐 Prompt 卡片
- (P2) Prompt 库弹窗（分类浏览 · 搜索 · 收藏 · 自定义）

**验收标准**：输入一个问题 → AI 流式回答（知识库内容）→ 来源引用可见 → 点击「保存回答」→ 填写名称和目录 → 在「私有数据」页面私有笔记区能找到该条记录。

---

## 变更索引

| 归档名 | 影响 Capability | 时间 |
|--------|----------------|------|
| _(暂无归档变更)_ | — | — |

---

## 查询指南

**"这个功能是怎么设计的？"** → 看 `spec.md`（行为契约）

**"为什么要做这个功能？"** → 看对应变更的 `proposal.md`（Why + 背景）

**"技术方案怎么选的？"** → 看对应变更的 `design.md`（Decisions 章节）

**"具体实现了哪些步骤？"** → 看对应变更的 `tasks.md`（TDD 任务列表）

**"需求编号对应哪里？"** → `docs/superpowers/specs/2026-05-05-requirements.md`
