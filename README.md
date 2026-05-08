# Knowledge Agent

A personal knowledge base powered by RAG. Ingest documents, web pages, and text into a vector database, then query them through a conversational AI assistant. V1 use case: personal finance.

## Features

- **Ingest** — upload files (PDF, MD, TXT), paste URLs, or enter text directly; content is chunked, embedded, and stored in Qdrant
- **Browse** — left-right knowledge browser: domain tree on the left, content viewer on the right
- **Search & Q&A** — ReAct agent retrieves relevant chunks and answers questions with source attribution (coming soon)
- **Private data** — per-user private collection alongside the shared knowledge base (coming soon)

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Vue 3 + Vite + Tailwind CSS |
| Backend | Python + Flask + LangGraph |
| Vector DB | Qdrant |
| LLM | Claude Haiku / Sonnet (Anthropic API) |
| Embeddings | OpenAI text-embedding-3-small |
| Metadata | SQLite |
| Deployment | Docker Compose |

## Architecture

```
┌─────────────────────────────────────────────┐
│                  Frontend                   │
│  IngestView · WikiView · ChatView · Private │
└──────────────────┬──────────────────────────┘
                   │ HTTP / SSE
┌──────────────────▼──────────────────────────┐
│               Flask API                     │
│  /ingest  /files  /wiki  /chat  /private    │
└────────┬──────────────────────┬─────────────┘
         │ LangGraph            │ SQLite
┌────────▼────────┐    ┌────────▼────────┐
│  IngestPipeline │    │   files table   │
│  Source Router  │    │  (metadata +    │
│  Fetch → Clean  │    │   file paths)   │
│  Chunk → Embed  │    └─────────────────┘
│  Store          │
└────────┬────────┘
         │ upsert
┌────────▼────────┐    ┌─────────────────┐
│     Qdrant      │    │  /app/uploads/  │
│  knowledge coll │    │  (raw files on  │
│  private coll   │    │   disk)         │
└─────────────────┘    └─────────────────┘
```

**Two LangGraph graphs:**
- `IngestPipeline` — deterministic: Source Router → Fetch → Clean → Chunk → Embed → Store
- `QAAgent` — ReAct agent with tools: `search_knowledge`, `search_private`, `get_entry`

**Two Qdrant collections:**
- `knowledge` — shared across all users
- `private` — per-user; every query must include a `user_id` filter

## Project Structure

```
backend/
  app/
    routes/       # Flask blueprints (ingest, files, wiki, chat, private)
    graphs/       # LangGraph graphs (ingest_pipeline.py, qa_agent.py)
    services/     # QdrantService, FileService, LLMService, EmbeddingService
    models/       # SQLite models
  db/
    schema.sql    # Database schema
  tests/          # pytest test suite

frontend/
  src/
    views/        # IngestView, WikiView, ChatView, PrivateView
    components/   # AppLayout, TreeNav, FileViewer, ...
    stores/       # Pinia stores (ingest)
    composables/  # useFileContent
    constants/    # domains.js
  tests/          # Vitest test suite

docs/
  superpowers/specs/   # Design specs
  log/                 # Daily dev logs (YYYY-MM-DD.md)
  design/              # Authoritative DESIGN.md (notion.md primary, linear.md backup)
```

## Quick Start

### Prerequisites
- Docker & Docker Compose
- Anthropic API key
- OpenAI API key

### Setup

```bash
# 1. Copy and fill in environment variables
cp .env.example .env

# 2. Start all services
docker compose up --build

# 3. Open the app
open http://localhost:3000
```

### Environment Variables

```env
LLM_PROVIDER=anthropic
ANTHROPIC_API_KEY=sk-ant-...
LLM_MODEL=claude-haiku-4-5-20251001

EMBEDDING_PROVIDER=openai
OPENAI_API_KEY=sk-...
EMBEDDING_MODEL=text-embedding-3-small

QDRANT_HOST=qdrant
QDRANT_PORT=6333

SQLITE_PATH=/app/data/knowledge_agent.db
UPLOADS_PATH=/app/uploads

FLASK_SECRET_KEY=change-me
```

## Development

### Backend

```bash
cd backend
pip install -r requirements.txt
pytest                    # run all tests
```

### Frontend

```bash
cd frontend
npm install
npm run dev               # dev server (hot reload)
npm test                  # vitest
npm run build             # production build
```

### Deploying changes

```bash
# Backend Python files — hot-swap without rebuild:
docker cp backend/app/routes/files.py python-agent-api-1:/app/app/routes/files.py
docker restart python-agent-api-1

# Frontend — requires image rebuild:
docker compose up --build frontend -d
# then Ctrl+Shift+R in browser
```

## Design Docs

- Architecture & requirements: `docs/superpowers/specs/2026-05-05-knowledge-agent-design.md`
- UI design system (authoritative): `docs/design/notion.md` (Linear backup at `docs/design/linear.md`); see `docs/design/README.md` for migration policy
- Daily dev log: `docs/log/`
