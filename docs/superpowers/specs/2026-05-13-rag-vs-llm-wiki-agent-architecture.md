# RAG vs LLM Wiki：两种知识库范式的对比与 Agent 架构演进

**日期：2026-05-13 | 作者：Austin | 状态：参考文档**

---

## 背景

本文源于对两个已落地项目的反思：

- **`wealth`（现：`rwh-overlay`）**：基于 Karpathy LLM Wiki 思路的结构化 Markdown 知识库，以 Claude Code / Skills 作为 agent runtime。无向量数据库，无后端服务。
- **`python-agent`**：向量数据库（Qdrant）+ LangGraph + Flask REST API + Vue 前端，标准 RAG 问答 agent，已具备多用户基础设施，部署于 NAS。

两个项目解决同一类问题（"怎么让 LLM 基于我的知识库回答问题"），却选择了截然不同的路径。这份文档的目的是：梳理两种范式的本质差异，结合 2025–2026 年 RAG 行业趋势和 Anthropic 自身的 agent 框架定位，形成有依据的架构判断，为未来项目演进提供参考。

---

## Section 1：两种范式是什么

### 1.1 Compiled Context 范式（wealth / rwh-overlay）

**核心思路**：知识由人工编译成结构化文件（Markdown wiki），Claude 在回答问题时直接读取这些文件作为上下文，不经过任何检索步骤。

**工作方式**：

```
原始资料 → [人工提炼] → 结构化 wiki 文件
                              ↓
用户提问 → Claude Code 读取相关 wiki → 生成回答
```

**runtime 是什么**：Claude Code / Claude Skills。用户通过 Claude Code 的 slash command 触发，Claude 本身承担 agent loop、工具调用、上下文管理的全部职责。

**关键特征**：
- 知识组织完全依赖人工，质量上限高但成本也高
- 零检索延迟（上下文直接加载）
- 知识量受限于 context window（当前 Claude 200K tokens ≈ 约 500 页文档）
- 部署即 Claude Code，无独立服务进程
- 单用户，不可作为 web 服务对外提供

### 1.2 Dynamic Retrieval 范式（python-agent）

**核心思路**：知识被切块、向量化后存入向量数据库，用户提问时通过相似度检索召回相关片段，注入 LLM prompt。即标准 RAG（Retrieval-Augmented Generation）流程。

**工作方式**：

```
原始文件 → [切块 → 向量化 → 存储] → Qdrant
                                         ↓
用户提问 → 向量检索 → 召回 top-k → 注入 prompt → LLM → 回答
```

**runtime 是什么**：独立的 Flask 服务 + LangGraph 编排，前端通过 REST API 访问。LLM（Claude）只是 pipeline 中的一个节点，不承担 orchestration 职责。

**关键特征**：
- 知识摄入自动化（文件、URL、文本均支持）
- 可处理任意规模知识库（不受 context window 限制）
- 检索质量是核心瓶颈
- 有独立的 web 服务层，天然支持多用户
- 部署复杂度更高（Docker Compose，三个服务）

### 1.3 两种范式的对比矩阵

| 维度 | Compiled Context | Dynamic Retrieval (RAG) |
|------|-----------------|------------------------|
| 知识组织方式 | 人工提炼，结构化 Markdown | 自动切块，向量化 |
| 检索机制 | 无检索，直接加载 | 向量相似度召回 |
| Agent runtime | Claude Code / Skills | 独立 web 服务 + LangGraph |
| 知识规模上限 | ~200K tokens（约 500 页） | 无上限 |
| 知识质量 | 高（人工把关） | 依赖切块和检索质量 |
| 多用户支持 | 不支持 | 支持（user_id 隔离） |
| 部署复杂度 | 极低（无服务） | 中等（Docker 三服务） |
| 适用场景 | 个人工具、小规模精品知识库 | 大规模知识库、多用户应用 |
| 典型代价 | 人工维护知识库成本 | 检索质量调优成本 |

---

## Section 2："RAG 要死了"这件事到底怎么回事

### 2.1 被质疑的是什么

"RAG is dead"的说法准确指向一个具体对象：**2023 年式的 naive RAG**——把文档切成固定大小的 chunk，存进 Pinecone，用余弦相似度召回 top-3，注入 prompt。

这套方案的核心问题不是 RAG 本身，而是：
1. **切块边界破坏语义**：一段完整的逻辑被切断，召回的 chunk 缺少前后文
2. **向量相似度 ≠ 逻辑相关性**：语义相近不代表对回答这个问题有用
3. **检索无状态**：不知道已经检索了什么，不能追问、不能消歧义
4. **关系信息丢失**：文档间的引用关系、实体关联在切块后不复存在

### 2.2 三个替代/演进方向

**方向一：CAG（Cache-Augmented Generation）**

思路：如果知识库足够小且相对稳定，直接把全部内容预加载进 LLM 的 KV cache，彻底跳过检索步骤。

实测数据（2026 年初生产环境）：
- CAG 平均查询时间：**2.33 秒**
- 标准 RAG 平均查询时间：**94.35 秒**
- 提升幅度：约 **40x**

Anthropic 的 prompt caching（在 cache 中保存 prompt 前缀，后续请求复用）让这个方案在经济上可行：对于不频繁变更的知识库，缓存命中后的 token 成本降低约 90%。

**适用条件**：知识库有边界（几百到几千页），更新频率低，用户查询多样但知识稳定。

> **注意**：`wealth` 和 `rwh-overlay` 当前的做法本质上已经是 CAG 的人工版本——只是没有自动化 prompt caching，而是靠 Skills/CLAUDE.md 手动管理上下文加载。

**方向二：GraphRAG（知识图谱检索）**

微软 2024 年中发布，2025 年快速普及。核心洞察：**向量相似度搜索丢失了关系信息**。

工作方式：在摄入阶段额外构建知识图谱（实体、关系、社区），查询时遍历图谱召回结构化关联信息，而不只是语义相近的片段。

对比：
- 标准 RAG：找"和这句话语义最像的段落"
- GraphRAG：找"和这个概念相关的所有实体及其关系"

**适用条件**：知识之间有丰富的实体关系（医疗、法律、金融）；需要全局摘要或多跳推理的查询。代价是摄入成本和图谱维护复杂度。

**方向三：Hybrid / Agentic RAG**

不再是"一次检索、一次生成"，而是 agent 控制多轮检索：
- 先检索，评估是否充分
- 如果不足，换关键词再检索
- 同时维护"已检索内容"的状态，避免重复
- 可以主动调用 API、数据库等外部工具

这是 RAG 演进的主流方向：**把 RAG 从 pipeline 变成 agent 的工具调用**。

### 2.3 判断框架：用哪个

```
知识库有边界且相对稳定？
  └─ 是 → 知识量 < 200K tokens？
             └─ 是 → CAG（直接加载或 prompt caching）
             └─ 否 → 切分为多个 CAG 单元，或 Hybrid RAG
  └─ 否 → 知识有强关系结构（实体图谱）？
              └─ 是 → GraphRAG 或 Knowledge Graph + RAG
              └─ 否 → Agentic RAG（多轮检索，agent 控制）
```

**结论**：RAG 没有死，naive RAG 被淘汰了。RAG 本身正在向 agent-controlled、multi-modal、graph-enhanced 的方向演进。

---

## Section 3：Anthropic 自己在做什么

### 3.1 Claude Agent SDK 的设计哲学

2025 年 3 月发布，核心设计是 **tool-use first**：agent 就是一个带工具的 Claude 模型，agent loop 极简——接收 prompt → 调用工具（包括调用其他 agent 作为工具）→ 返回结果。Anthropic 有意不在框架层加抽象，依赖 Claude 本身的能力做推理和决策。

**SDK 的强项**：
- 与 Claude 深度集成（extended thinking、computer use、prompt caching 开箱即用）
- MCP 原生支持（Model Context Protocol，标准化跨 agent 工具发现）
- 适合 Claude-only 环境，快速原型，代码密集型任务
- Agent Skills 标准（可复用的任务包：指令 + 脚本 + 资源）

**SDK 的弱项**：
- 无内建的多用户状态管理
- 有状态的长流程（带分支、暂停、人机交互的工作流）需要大量自定义代码
- 水平扩展需要自行处理

### 3.2 LangGraph 的定位

LangGraph 是**有状态、多步 agent 工作流的编排框架**。核心能力：
- 图节点 = 独立 agent 或处理步骤
- 内建状态持久化（断点续跑）
- Time-travel debugging（可以回溯到任意节点状态）
- Human-in-the-loop 模式（在任意节点暂停等待人工输入）
- 天然支持多 agent 拓扑（并行、串行、条件分支）

python-agent 目前的 LangGraph 使用相对轻量（IngestPipeline + QAAgent），只是用了它的图编排能力，没有深入使用持久化和 human-in-the-loop。

### 3.3 两者的关系：互补而非竞争

| 维度 | Claude Agent SDK | LangGraph |
|------|-----------------|-----------|
| 核心职责 | LLM 调用 + 工具执行 | 工作流编排 + 状态管理 |
| 擅长 | 单次复杂推理、代码任务 | 多步有状态流程、多 agent 协调 |
| 多用户 | 需自行实现 | 内建持久化，自然支持 |
| 部署 | 轻量（CLI 级） | 需要后端服务 |
| LLM 绑定 | 绑定 Claude | LLM 无关 |

**推荐组合方式**：LangGraph 作为工作流骨架（负责状态管理、编排、持久化），Anthropic API 负责每个节点内的 LLM 调用。这正是 python-agent 当前的做法，方向是正确的。

### 3.4 MCP 的角色

MCP（Model Context Protocol）是 Anthropic 主导的跨 agent 工具发现标准。作用：
- Agent A 可以动态发现并调用 Agent B 暴露的工具，无需硬编码接口
- 工具定义与 LLM 解耦，任何支持 MCP 的模型都可以用
- Claude Code 的 Skills 系统部分基于此思路构建

在多 agent 架构中，MCP 是未来实现"agent 即服务"的基础协议。

---

## Section 4：Claude-as-runtime 的边界在哪里

### 4.1 Claude-as-runtime 适合的场景

以下场景用 Claude Code / Skills 作为 runtime 是合理且高效的：

- **个人工具**：只有一个用户（你自己），无需用户隔离
- **知识规模有限**：知识库能在 context window 内装下
- **交互方式是 CLI / 编辑器**：用户通过 Claude Code 触发，不需要 web UI
- **快速迭代**：Skills 的修改比部署一个 web app 快 10 倍
- **知识质量优先于规模**：宁可少而精，不要多而杂

wealth 和 rwh-overlay 都符合这些条件。**当前的做法是合适的，不需要改。**

### 4.2 Claude-as-runtime 跨不过的墙

当出现以下需求时，Claude-as-runtime 无法满足：

| 需求 | 为什么 Claude-as-runtime 不行 |
|------|-------------------------------|
| 多用户访问 | Claude Code 是单用户 CLI，无用户隔离机制 |
| 常驻后台服务 | Claude Code 是交互式会话，不是 daemon |
| Web UI / API | 无独立 HTTP 服务层 |
| 独立的 agent loop | Claude Code 本身 IS the agent loop，无法注入自定义逻辑 |
| 用户数据隔离 | 无 session 管理，无 user context 隔离 |
| 异步任务队列 | 无 job queue 机制 |

**核心判断标准**：如果你需要"让这个 agent 在我不开着 Claude Code 的时候也能运行"，或者"让其他人也能用这个 agent"，那就需要一个真正的 agent 应用架构。

### 4.3 对 python-agent 的确认

python-agent 的架构选择是正确的：
- 有独立的 Flask 服务层（独立运行，无需 Claude Code）
- 有用户认证和 user_id 隔离（私有数据严格隔离）
- LangGraph 作为独立编排层（Claude 只是 LLM 节点，不是 runtime）
- Docker 部署（可持续运行于 NAS）

它的问题不是架构方向错了，而是**知识检索层用了 naive RAG**，这是可以独立演进的组件。

---

## Section 5（附录）：rwh-overlay 类项目的架构建议

### 5.1 路径一：继续个人工具路线（推荐当前阶段）

**当前状态已经足够好**，主要可以做的增强：

**增强点 1：CAG 化**
将高频使用的核心知识（如股票分析框架、交易规则等）整理为结构化的 prompt 前缀，配合 Anthropic prompt caching：

```python
# 把核心知识库作为 cached system prompt 的一部分
# 首次请求缓存，后续请求免费命中
client.messages.create(
    model="claude-sonnet-4-6",
    system=[
        {
            "type": "text",
            "text": "<核心知识库内容，几百页>",
            "cache_control": {"type": "ephemeral"}  # 5分钟 TTL，频繁使用自动刷新
        }
    ],
    ...
)
```

这样可以把每次 Skills 调用的延迟从"每次重新加载所有上下文"降低到"命中 cache，几乎零延迟"。

**增强点 2：知识分层**
- `core/`：常驻上下文，每次都加载（规则、框架、个人偏好）
- `reference/`：按需加载（具体 ticker 分析、历史数据）
- `session/`：本次会话产生的数据（今日扫描结果、临时笔记）

### 5.2 路径二：演进为多用户 Agent 应用

如果未来 rwh-overlay 想变成一个真正的 agent 应用（多用户、web UI、常驻后台），推荐架构：

```
┌─────────────────────────────────────────────────────┐
│                    前端层                            │
│  Vue 3 / React  →  REST API + SSE 流式              │
└───────────────────────┬─────────────────────────────┘
                        │
┌───────────────────────▼─────────────────────────────┐
│                  编排层（LangGraph）                  │
│  IngestGraph: 知识摄入 pipeline                      │
│  QAAgent: ReAct agent（搜索→推理→回答）              │
│  SchedulerAgent: 定时任务（如 morning scan）         │
└──────┬──────────┬───────────────┬────────────────────┘
       │          │               │
┌──────▼──┐  ┌───▼────┐  ┌───────▼──────┐
│  知识层  │  │ 私有层 │  │   工具层     │
│  CAG:   │  │ SQLite │  │  yfinance    │
│  核心   │  │ user   │  │  web search  │
│  知识库  │  │ data   │  │  MCP tools   │
│  + Hybrid│  │        │  │              │
│  RAG:   │  └────────┘  └──────────────┘
│  动态   │
│  内容   │
└──────────┘
```

**关键技术选型**：

| 组件 | 选型 | 理由 |
|------|------|------|
| LLM 调用 | Anthropic API（非 Agent SDK） | 直接调用，灵活控制，不绑定 CLI |
| 编排 | LangGraph | 有状态工作流，多 agent，持久化 |
| 稳定知识 | CAG（prompt caching） | 低延迟，成本优化 |
| 动态/大规模知识 | Hybrid RAG（向量 + BM25） | 精度优于纯向量检索 |
| 私有数据 | SQLite + 独立 Qdrant collection | 严格 user_id 隔离 |
| 工具发现 | MCP | 标准协议，未来可扩展 |
| 后端 | Flask / FastAPI | 轻量，python 生态 |
| 部署 | Docker Compose on NAS | 与 python-agent 一致 |

### 5.3 演进建议

**不建议现在重构 rwh-overlay**。当前作为个人工具运行良好，改成 web app 会带来大量基础设施成本，但用户就一个（你）。

**合理的演进时机**：
1. 知识库规模超出 context window（rwh-overlay 当前内容应该远未到这个量级）
2. 需要家庭成员或其他人使用同一个 agent
3. 需要常驻后台运行的定时任务（目前通过 Skills 手动触发足够）

**最有价值的单点改进**（无论路径）：在 Skills 调用链中加入 Anthropic prompt caching，把核心知识前缀缓存化，降低每次调用的延迟和成本。

---

## 结语

两种范式没有优劣之分，只有适用场景之分：

- **Compiled Context（LLM Wiki + Skills）**：个人工具的理想形态，CAG 趋势印证了这个方向的正确性，不是落后而是领先了一步
- **Dynamic Retrieval（RAG + web app）**：多用户 agent 应用的必经之路，当前 naive RAG 可以升级，但架构方向是对的

真正的分水岭不是"哪种技术更先进"，而是：**这个 agent 是给自己用的工具，还是给其他人用的应用。** 搞清楚这个问题，架构选择就自然清晰了。

---

*参考资料：*
- *[RAG is DEAD! (Medium, 2025)](https://medium.com/@reliabledataengineering/rag-is-dead-and-why-thats-the-best-news-you-ll-hear-all-year-0f3de8c44604)*
- *[The RAG era is ending for agentic AI (VentureBeat)](https://venturebeat.com/data/the-rag-era-is-ending-for-agentic-ai-a-new-compilation-stage-knowledge-layer-is-what-comes-next)*
- *[Standard RAG Is Dead: Why AI Architecture Split in 2026](https://ucstrategies.com/news/standard-rag-is-dead-why-ai-architecture-split-in-2026/)*
- *[Building agents with the Claude Agent SDK (Anthropic)](https://www.anthropic.com/engineering/building-agents-with-the-claude-agent-sdk)*
- *[From RAG to Context: A 2025 year-end review (RAGFlow)](https://ragflow.io/blog/rag-review-2025-from-rag-to-context)*
- *[2026 AI Agent Framework Showdown (QubitTool)](https://qubittool.com/blog/ai-agent-framework-comparison-2026)*
