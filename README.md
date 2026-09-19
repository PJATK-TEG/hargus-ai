# Hargus AI — AI Candidate Analyzer

![HARGUS-AI](./docs/hero.png)

An AI-powered recruiting platform that ingests candidate CVs, interview transcripts, and background data, then produces structured scoring and narrative PDF reports using a multi-agent LangGraph pipeline orchestrated by Temporal.

## What It Does

- **Vacancies & Candidates** — manage open roles and candidate profiles via a REST API
- **Document Ingestion** — parse PDFs and text files, chunk and embed into pgvector
- **Multi-Agent Analysis** — 7 LangGraph agents run in parallel and sequence: JD analysis, candidate extraction, interview insights, consistency check, profile extraction, report drafting, candidate query
- **Scoring** — deterministic weighted score: skill 40% + experience 35% + interview 25% − risk penalty
- **PDF Reports** — WeasyPrint + Jinja2 rendered report, stored locally or in S3/MinIO
- **Observability** — Langfuse traces all LLM calls and records custom scoring metrics per workflow run
- **Frontend Dashboard** — React + TypeScript UI with live API mode or static demo mode (set `VITE_MODE=DEMO`)

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React + Vite + TypeScript + Tailwind |
| Backend API | FastAPI (Python) |
| Workflow orchestration | Temporal |
| Agent framework | LangGraph + LangChain |
| LLM | Any OpenAI-compatible API (OpenRouter by default; Ollama for fully local) |
| Embeddings | Ollama (`nomic-embed-text`) |
| Vector search | pgvector (Postgres extension) |
| Object storage | MinIO (local) or S3 |
| PDF rendering | WeasyPrint + Jinja2 |
| LLM observability | Langfuse (optional) |
| DB migrations | Alembic |
| Dependency management | uv |
| Task runner | Taskfile |
| Containerization | Docker Compose |

## Getting Started

See [`docs/local-dev-guide.md`](./docs/local-dev-guide.md) for the full setup walkthrough.

### Prerequisites

- Docker Desktop
- Python 3.11+
- [`uv`](https://docs.astral.sh/uv/) (`pip install uv`)
- [`task`](https://taskfile.dev/installation/)
- Node.js 18+
- An OpenAI-compatible API key (e.g. [OpenRouter](https://openrouter.ai)) — or Ollama running locally

### Quick Start

```bash
# 1. Copy env file and fill in your API key
cp .env.example .env
# Edit .env — set HARGUS_OPENAI_API_KEY and optionally HARGUS_LLM_MODEL

# 2. Start infrastructure (Postgres, Temporal, MinIO, Langfuse)
task docker:up

# 3. Install backend dependencies and run migrations
task backend:install
task backend:migrate

# 4. Start API and worker (two separate terminals)
task backend:dev      # http://localhost:8000
task backend:worker

# 5. Start frontend
task frontend:dev     # http://localhost:3000
```

For embeddings, Ollama must be running locally with `nomic-embed-text` pulled:
```bash
task ollama:start     # in a separate terminal
ollama pull nomic-embed-text
```

To use fully local LLMs instead of OpenRouter, set `HARGUS_LLM_PROVIDER=ollama` and `HARGUS_LLM_MODEL=<model>` in `backend/.env`.

## Project Structure

```
hargus-ai/
├── frontend/          # React + Vite dashboard
├── backend/           # FastAPI + Temporal worker
│   └── src/hargus_api/
│       ├── ai/        # LangGraph agents + tracing
│       ├── db/        # SQLAlchemy models + Alembic migrations
│       ├── storage/   # Local / S3 abstraction
│       ├── pdf/       # Report renderer
│       └── temporal/  # Workflows and activities
├── docs/              # Architecture docs and guides
├── .env.example       # Environment variable template
├── Taskfile.yml       # Dev task runner
└── docker-compose.yml # Full local stack
```

## Documentation

- [`docs/local-dev-guide.md`](./docs/local-dev-guide.md) — full local setup and end-to-end flow
- [`docs/codebase_overview.md`](./docs/codebase_overview.md) — architecture and code map
- [`docs/api_overview.md`](./docs/api_overview.md) — REST API reference
- [`docs/backend_overview.md`](./docs/backend_overview.md) — backend structure and workflow details
