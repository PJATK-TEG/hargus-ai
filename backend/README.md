# Hargus API Backend

FastAPI backend with a Temporal worker that runs the full AI candidate analysis pipeline.

## What's Here

- **REST API** (`api/routes/`) — vacancies, candidates, AI tasks, background jobs, health
- **Temporal workflow** (`temporal/workflows/candidate_analysis.py`) — 13 activities across 7 phases: document loading → parsing → chunking/embedding → parallel LLM analysis → scoring → PDF rendering → storage
- **LangGraph agents** (`ai/agents/`) — JD extraction, candidate extraction, interview insights, consistency check, profile extraction, report drafting, candidate query
- **Deterministic scoring** (`temporal/activities/scoring.py`) — skill 40% + experience 35% + interview 25% − risk penalty; no LLM involved
- **pgvector storage** (`db/`) — SQLAlchemy async models, Alembic migrations, vector search for RAG on transcripts
- **Object storage** (`storage/`) — local filesystem or S3/MinIO, selected by `HARGUS_STORAGE_BACKEND`
- **PDF rendering** (`pdf/`) — WeasyPrint + Jinja2
- **Langfuse tracing** (`ai/tracing.py`) — all LLM calls traced via CallbackHandler; custom scores recorded at workflow completion

## Configuration

Copy `backend/.env.example` to `backend/.env`. All settings use the `HARGUS_` prefix and are loaded via `get_settings()` in `config.py`.

Key variables:

| Variable | Description |
|---|---|
| `HARGUS_DATABASE_URL` | PostgreSQL connection string (`postgresql+asyncpg://...`) |
| `HARGUS_TEMPORAL_ENABLED` | Set `true` to run real workflows; `false` queues tasks in memory |
| `HARGUS_LLM_PROVIDER` | `openai` (OpenAI-compatible API) or `ollama` |
| `HARGUS_LLM_MODEL` | Model name, e.g. `openai/gpt-4o` or `llama3.2:3b` |
| `HARGUS_OPENAI_API_KEY` | API key for OpenAI-compatible endpoint |
| `HARGUS_OPENAI_BASE_URL` | Base URL, defaults to `https://openrouter.ai/api/v1` |
| `HARGUS_EMBEDDING_PROVIDER` | `ollama` (requires local Ollama with `nomic-embed-text`) |
| `HARGUS_LANGFUSE_ENABLED` | Set `true` to enable Langfuse tracing |

## Running Locally

```bash
task backend:install   # uv sync --group dev
task backend:migrate   # alembic upgrade head
task backend:dev       # FastAPI on :8000 with --reload
task backend:worker    # Temporal worker (separate terminal)
```

## Tests

```bash
task backend:test      # pytest backend/tests
task backend:lint      # ruff check
```
