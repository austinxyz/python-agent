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
