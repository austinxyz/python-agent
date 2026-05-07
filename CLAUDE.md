# Knowledge Agent

通用知识库 Agent。将原始知识摄入向量数据库，结合用户私有数据，通过 RAG 提供专业问答。V1 场景：个人理财。

## 技术栈

- **前端**：Vue 3 + Vite（`frontend/`）
- **后端**：Python + Flask + LangGraph（`backend/`）
- **向量库**：Qdrant（Docker 容器，port 6333）
- **LLM**：Claude Haiku/Sonnet（Anthropic API，可配置切换 OpenAI）
- **Embeddings**：OpenAI text-embedding-3-small
- **元数据**：SQLite（文件注册表、笔记）
- **部署**：Docker Compose → NAS → Railway

## 项目结构

```
backend/app/
  routes/          # Flask 路由（ingest / wiki / chat / private / files / prompts）
  graphs/          # LangGraph（ingest_pipeline.py · qa_agent.py）
  services/        # Qdrant · 文件 · LLM 服务
  models/          # SQLite 数据模型

frontend/src/
  views/           # WikiView · IngestView · ChatView · PrivateView
  components/      # TreeNav · ChatMessage · PromptLibrary · SaveNoteModal
```

## 核心设计决策

**LangGraph 两个 Graph：**
- `IngestPipeline`：确定性流水线，Source Router → Fetch → Clean → Chunk → Embed → Store
- `QAAgent`：ReAct Agent，工具：`search_knowledge` / `search_private` / `get_entry`

**Qdrant 两个集合：**
- `knowledge`：公共知识库，所有用户共享
- `private`：私有数据，查询时必须附加 `user_id` 过滤，V1 固定 `user_id="default"`

**原始文件永久保留：** 摄入后存 `/app/uploads/{user_id}/{file_id}/`，SQLite `files` 表记录元数据。

## 开发规范

- 私有数据查询必须附加 `user_id` 过滤，不能遗漏
- SSE 流式响应用 Flask `Response(stream_with_context(...))`
- LLM 和 Embedding provider 通过环境变量切换，不硬编码
- `TreeNav.vue` 是通用组件，知识库和文件管理共用，不要重复实现

## 环境变量（.env）

```
LLM_PROVIDER=anthropic
ANTHROPIC_API_KEY=sk-ant-...
LLM_MODEL=claude-haiku-4-5-20251001

EMBEDDING_PROVIDER=openai
OPENAI_API_KEY=sk-...
EMBEDDING_MODEL=text-embedding-3-small

QDRANT_HOST=qdrant
QDRANT_PORT=6333

FLASK_SECRET_KEY=...
```

## 设计文档

`docs/superpowers/specs/2026-05-05-knowledge-agent-design.md`

## 前端 UI 设计规范

### 技术基础
- **Tailwind CSS** + HSL CSS 变量（`src/style.css`）
- **lucide-vue-next** 提供图标
- **@tailwindcss/typography** 用于 `prose` 富文本渲染
- CSS token 在 `tailwind.config.cjs` 中映射：`bg-background`、`text-foreground`、`bg-primary`、`border-border` 等

### 页面整体结构
```
h-screen flex flex-col bg-gradient-to-br from-blue-50 via-purple-50 to-pink-50
```
- 页面根容器：`h-screen flex flex-col`，防止内部滚动溢出
- 背景：蓝→紫→粉渐变（`from-blue-50 via-purple-50 to-pink-50`）

### 页头（Page Header）
```html
<div class="bg-gradient-to-r from-blue-600 to-purple-600 shadow-lg px-6 py-4 flex-shrink-0">
  <h1 class="text-2xl font-bold text-white">页面标题</h1>
  <p class="text-xs text-blue-100 mt-1">副标题说明文字</p>
</div>
```
- 蓝→紫横向渐变，白色文字，`flex-shrink-0` 固定高度

### 卡片（Card）
```html
<div class="bg-white rounded-xl border border-gray-200 shadow-sm p-4">
```
- 白底、`rounded-xl`、`border-gray-200`、`shadow-sm`

### 按钮
| 用途 | 样式 |
|------|------|
| 主操作（提交/摄入） | `bg-gradient-to-r from-blue-500 to-purple-600 hover:from-blue-600 hover:to-purple-700 text-white font-bold rounded-xl shadow-md` |
| 次操作（新建） | `bg-gradient-to-r from-green-400 to-emerald-500 text-white font-bold rounded-lg shadow-md` |
| 激活状态 tab | `bg-gradient-to-r from-blue-500 to-indigo-500 text-white border-transparent shadow-md` |
| 默认状态 tab | `bg-white text-gray-600 border-gray-200 hover:border-indigo-300` |

### 侧边栏分区 Header
```html
<div class="px-4 py-3 border-b border-gray-200 bg-gradient-to-r from-indigo-500 to-purple-500">
  <h2 class="text-sm font-semibold text-white">标题</h2>
</div>
```

### 选中 / 激活行（侧边栏列表项）
```
bg-gradient-to-r from-blue-50 to-purple-50 border-l-4 border-l-blue-600 shadow-sm
```
未选中 hover：`hover:bg-gradient-to-r hover:from-gray-50 hover:to-blue-50`

### 徽章（Badge / Pill）
```html
<!-- 文件数量 -->
<span class="px-2 py-0.5 text-[10px] font-bold rounded-full bg-indigo-100 text-indigo-600">N 篇</span>
<!-- 领域标签 -->
<span class="px-3 py-1 text-sm font-bold rounded-full bg-gradient-to-r from-blue-500 to-indigo-500 text-white">退休规划</span>
```

### 空状态占位
```html
<div class="flex flex-col items-center justify-center h-48 gap-3 text-gray-400">
  <span class="text-4xl">📂</span>
  <p class="text-sm">说明文字</p>
</div>
```

### 输入框 / 文本区
```html
<!-- 单行 -->
<input class="w-full px-3 py-2.5 rounded-lg border border-gray-200 bg-gray-50 text-sm
              placeholder:text-gray-400 focus:outline-none focus:ring-2 focus:ring-indigo-400
              focus:border-transparent transition-all" />
<!-- 多行文本（摄入文本框） -->
<textarea class="... resize-y" style="min-height: 55vh" />
```

### AppLayout 导航栏
- 可折叠侧边栏：展开 `w-56`，收起 `w-16`，`transition-all duration-300`
- 激活路由：`bg-primary/10 text-primary`
- 图标库：`lucide-vue-next`（Brain、BookOpen、Upload、MessageSquare、Lock、ChevronsLeft、ChevronsRight）

### 右侧面板内容区
```html
<div class="bg-gradient-to-r from-indigo-600 to-purple-600 px-6 py-4 flex-shrink-0 shadow-md">
  <!-- 面板标题行 -->
</div>
<div class="flex-1 overflow-y-auto p-6">
  <!-- 内容 -->
</div>
```
内容区用 `flex-1 overflow-y-auto` 保证标题固定、内容可滚动。

---

## 已知陷阱（过去犯过的错误）

### Windows 环境

- **Bash tool 不能用 Windows 路径**：`cd C:\Users\...` 在 Bash tool 里会失败（Git Bash 把反斜杠吃掉）。凡是涉及 Windows 路径的 shell 操作，必须用 **PowerShell tool**。
- **docker cp 路径格式**：在 PowerShell 中用 `docker cp "C:/Users/.../file.py" container:/path/file.py`（正斜杠，加引号）。不能用 Bash tool 执行这条命令。

### Docker 部署

- **前端改动不会热更新**：nginx 容器服务的是编译后的 `dist/`，修改 Vue 文件后必须 `docker compose up --build frontend -d` 重新构建，然后浏览器 `Ctrl+Shift+R` 强刷。不要反复检查代码以为是 bug。
- **后端 Python 文件可热替换**：`docker cp` 复制新文件到容器后 `docker restart python-agent-api-1` 即可，不需要重新 build image。
- **SQLite 环境变量名是 `SQLITE_PATH`**，不是 `DATABASE_PATH`。手写调试脚本时用 `os.environ.get('SQLITE_PATH', 'knowledge_agent.db')`，否则查到的是空库。

### Ingest Pipeline

- **text / url 摄入不自动保存原文到磁盘**：原始设计只有 `source_type=file` 才调用 `file_svc.save()`。text 和 url 的清洗后内容（`raw_content`）需要在 `store_node` 里显式保存为 `{file_id}.txt`，否则 `/content` 端点 404。
- **URL `/content` 端点返回原始 HTML**：旧版直接返回 `resp.text`，前端用 `<pre>` 包裹后显示源码。正确做法：先看本地文件是否存在，存在则直接 serve；否则 re-fetch 并经 `_html_to_text()` 提取纯文本再返回。

### Git

- **本地改动可能跨 session 未提交**：每次 push 前先 `git status` 确认没有遗漏的 unstaged 文件，上一个 session 的改动可能还在工作区里。

## Dev Log Practice

**每完成一个功能批次，必须更新当天的开发日志。**

日志文件路径：`docs/log/YYYY-MM-DD.md`（按日期命名，当天若无则新建）

### 每个日志条目包含

```markdown
### N. 功能名称
**提交：** `<git hash>`

**功能：**
- 简洁描述做了什么（bullet points）

**代码审查发现（如有）：**
| 级别 | 问题 | 修复 |

**测试：** X tests 全部通过（新增 Y 个）
```

### 规则

- **每次 commit 后**更新日志（或每个功能批次结束时）
- **待完成事项**用 `- [ ]`，已完成用 `- [x]`
- 日志结尾保留「待完成」章节，列出下一批次或已知问题
- 任务清单中始终包含 **`update log`** 这一步
