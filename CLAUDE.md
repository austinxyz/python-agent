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
