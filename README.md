# Hargus AI — AI Candidate Analyzer

![HARGUS-AI](./docs/hero.png)

An AI-powered recruiting platform that ingests candidate CVs, interview transcripts, and background data, then produces structured scoring and narrative PDF reports using a multi-agent LangGraph pipeline orchestrated by Temporal.

## What It Does

- **Vacancies & Candidates** — manage open roles and candidate profiles via a REST API
- **Document Ingestion** — parse PDFs and text files, chunk and embed with Ollama into pgvector
- **Multi-Agent Analysis** — 4 parallel LangGraph agents: JD analysis, candidate extraction, interview insights, consistency check
- **Scoring** — weighted score: skill 40% + experience 35% + interview 25% − risk penalty
- **PDF Reports** — WeasyPrint + Jinja2 rendered report, stored locally or in S3/MinIO
- **Frontend Dashboard** — React + TypeScript UI; runs in **Demo mode** (static mocks) or **Live mode** (real API)

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React + Vite + TypeScript + Tailwind |
| Backend API | FastAPI (Python) |
| Workflow orchestration | Temporal |
| Agent framework | LangGraph |
| LLM runtime | Ollama (local, no external API key needed) |
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
- [`uv`](https://docs.astral.sh/uv/getting-started/installation/)
- [`task`](https://taskfile.dev/installation/) (`winget install Task.Task` on Windows)
- Node.js 18+

### Quick Start

```bash
# 1. Start infrastructure (Postgres, Temporal, MinIO, Ollama, Langfuse)
task docker:up

# 2. Install backend dependencies and run migrations
task backend:install
task backend:migrate

# 3. Start API and worker
task backend:dev      # http://localhost:8000
task backend:worker

# 4. Start frontend
task frontend:dev     # http://localhost:3000
```

The frontend runs in **Demo mode** by default (set `VITE_MODE=DEMO` in `frontend/.env`).  
To connect it to the live backend, leave `VITE_MODE` unset and set `VITE_API_URL=http://localhost:8000/api/v1`.

## Project Structure

```
hargus-ai/
├── frontend/          # React + Vite dashboard
├── backend/           # FastAPI + Temporal worker
│   └── src/hargus_api/
│       ├── ai/        # LangGraph agents
│       ├── db/        # SQLAlchemy models + Alembic migrations
│       ├── storage/   # Local / S3 abstraction
│       ├── pdf/       # Report renderer
│       └── temporal/  # Workflows and activities
├── docs/              # Architecture docs and guides
├── Taskfile.yml       # Dev task runner
└── docker-compose.yml # Full local stack
```

## Documentation

- [`docs/local-dev-guide.md`](./docs/local-dev-guide.md) — full local setup and end-to-end flow
- [`docs/codebase_overview.md`](./docs/codebase_overview.md) — architecture and code map
- [`docs/api_overview.md`](./docs/api_overview.md) — REST API reference
- [`docs/backend_overview.md`](./docs/backend_overview.md) — backend structure and workflow details
