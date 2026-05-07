# Codebase Overview

## Current Shape

- `frontend/` — React + Vite + TypeScript dashboard using live API calls to the backend.
- `backend/` — FastAPI API + Temporal worker implementing a full AI candidate analysis pipeline (LangGraph agents, pgvector embeddings, PDF reports, S3/local storage).
- `docs/` — architecture diagrams and overview docs.
- `Taskfile.yml` — common repo tasks for frontend, backend, Docker, and Alembic migrations.
- `docker-compose.yml` — full local stack: Postgres (pgvector), Temporal + UI, Langfuse, MinIO, API service.

## Product Model

The repo centers on a recruiting workflow:

- **Vacancies** — open positions with status, requirements, and candidate counts
- **Candidates** — full profiles with parsed CV fields, scores, tags, and files
- **Candidate files** — CVs, transcripts, notes, background checks
- **AI tasks** — async Temporal workflows: candidate analysis, background checks, comparisons
- **Analysis reports** — structured scoring results persisted to Postgres after workflow completion

## Frontend

The frontend makes real API calls to the backend at `VITE_API_URL`.

Key files:
- `src/lib/api.ts` — typed fetch client for all backend endpoints
- `src/vite-env.d.ts` — Vite env type declarations (`VITE_API_URL`)
- `src/pages/` — pages fetch data on mount

## Backend

The backend is a FastAPI gateway + Temporal workflow engine:

- `src/hargus_api/api/routes/` — REST endpoints (vacancies, candidates, ai tasks, background checks)
- `src/hargus_api/services/` — domain services and workflow launch logic
- `src/hargus_api/temporal/` — Temporal client, `CandidateAnalysisWorkflow`, activities
- `src/hargus_api/ai/` — LangGraph agents (JD, candidate extraction, interview, consistency, report)
- `src/hargus_api/db/` — SQLAlchemy async models, Alembic migrations, repositories
- `src/hargus_api/storage/` — `LocalStorage` / `S3Storage` abstraction
- `src/hargus_api/pdf/` — WeasyPrint + Jinja2 report renderer
- `src/hargus_api/worker.py` — Temporal worker process (registers all 13 activities + 2 workflows)

## API Endpoints

```
GET  /api/v1/health
GET  /api/v1/vacancies
GET  /api/v1/vacancies/{id}
GET  /api/v1/vacancies/{id}/candidates
GET  /api/v1/candidates
GET  /api/v1/candidates/{id}
GET  /api/v1/candidates/{id}/messages
POST /api/v1/ai/tasks               — triggers CandidateAnalysisWorkflow
GET  /api/v1/ai/tasks/{id}          — poll workflow status
GET  /api/v1/background/sources
POST /api/v1/background/checks
GET  /api/v1/background/checks/{id}
POST /api/v1/background/sources/{source}/search
```

All response shapes use camelCase JSON aliases (Pydantic `Field(alias=...)`).

## AI Workflow (Temporal)

When `HARGUS_TEMPORAL_ENABLED=true`, submitting an AI task starts `CandidateAnalysisWorkflow`:

1. **Load documents** — list candidate files from storage
2. **Parse documents** — extract text from PDFs / plain text
3. **Chunk & embed** — split text, embed with Ollama, store in pgvector
4. **4 parallel agents** — JD analysis, candidate extraction, interview insights, consistency check (all LangGraph StateGraphs)
5. **Consolidate** — deterministic skill matching and coverage scoring
6. **Score** — weighted scoring: skill 40%, experience 35%, interview 25%, minus risk penalty
7. **Draft report** — LangGraph report agent synthesizes narrative
8. **Render PDF** — WeasyPrint + Jinja2, uploaded to storage
9. **Persist** — `AnalysisReport` saved to Postgres, `WorkflowRun` marked complete

## Tooling

| Tool | Purpose |
|------|---------|
| `uv` | Python dependency management |
| FastAPI | HTTP API framework |
| Temporal | Durable workflow orchestration |
| Alembic | Database migrations |
| LangGraph | Agent state machine framework |
| pgvector | Vector similarity search in Postgres |
| Langfuse | LLM observability (optional, local or hosted) |
| Taskfile | Dev task runner |
| Docker Compose | Full local stack |
