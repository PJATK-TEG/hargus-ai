# Backend Overview

## Purpose

FastAPI gateway + Temporal workflow engine for AI-powered candidate analysis. Handles document ingestion, LangGraph agent orchestration, pgvector embeddings, PDF report generation, and S3/local file storage.

## Structure

```
backend/src/hargus_api/
├── main.py                  # FastAPI app entrypoint
├── config.py                # Settings and environment wiring (Pydantic)
├── worker.py                # Temporal worker process (13 activities + 2 workflows)
├── api/routes/              # HTTP route handlers (vacancies, candidates, ai tasks, background)
├── services/                # Domain services and workflow launch logic
├── temporal/
│   ├── client.py            # Temporal client with retry connection
│   ├── workflows/
│   │   └── candidate_analysis.py   # CandidateAnalysisWorkflow (9-step pipeline)
│   ├── activities/
│   │   ├── ingestion.py     # Load + parse candidate documents
│   │   ├── embedding.py     # Chunk text, embed with Ollama, store in pgvector
│   │   ├── analysis.py      # 4 parallel LangGraph agents
│   │   ├── scoring.py       # Weighted scoring (skill 40%, exp 35%, interview 25%)
│   │   └── reporting.py     # Report draft + WeasyPrint PDF render + storage upload
│   └── models.py            # Shared Temporal input/output models
├── ai/                      # LangGraph agents (JD, candidate, interview, consistency, report)
├── db/
│   ├── base.py              # SQLAlchemy declarative base
│   ├── models.py            # ORM models: WorkflowRun, AnalysisReport, DocumentChunk
│   ├── repositories/        # Async repository classes
│   └── migrations/          # Alembic async migrations
├── storage/                 # LocalStorage / S3Storage abstraction
└── pdf/                     # WeasyPrint + Jinja2 report renderer
```

## AI Workflow

When `HARGUS_TEMPORAL_ENABLED=true`, `POST /api/v1/ai/tasks` starts `CandidateAnalysisWorkflow`:

1. Load candidate files from storage
2. Parse PDFs and plain text documents
3. Chunk text, embed with Ollama, store vectors in pgvector
4. Run 4 parallel LangGraph agents: JD analysis, candidate extraction, interview insights, consistency check
5. Consolidate with deterministic skill matching and coverage scoring
6. Compute weighted score: skill 40% + experience 35% + interview 25% − risk penalty
7. Draft narrative report via LangGraph report agent
8. Render PDF with WeasyPrint + Jinja2, upload to storage
9. Persist `AnalysisReport` to Postgres, mark `WorkflowRun` complete

## Key Environment Variables

| Variable | Purpose |
|----------|---------|
| `DATABASE_URL` | PostgreSQL connection string (`postgresql+asyncpg://...`) |
| `HARGUS_TEMPORAL_ENABLED` | Set to `true` to enable real workflow execution |
| `HARGUS_TEMPORAL_SERVER_URL` | Temporal server address (`host:port`) |
| `HARGUS_STORAGE_BACKEND` | `local` or `s3` |
| `HARGUS_LLM_BASE_URL` | Ollama base URL for embeddings and agents |
| `LANGFUSE_*` | Optional LLM observability (host, public key, secret key) |

## Database

Uses SQLAlchemy async with pgvector extension. Migrations managed by Alembic:

```bash
task backend:migrate           # apply migrations
task backend:migrate:new -- -m "description"  # generate new migration
```

## What Is Still Missing

- Authentication and RBAC
- Real data behind GET endpoints (currently returns empty lists without mock data)
- Audit / event logging
- Background check activities (stubs registered, not implemented)
- Candidate comparison workflow
