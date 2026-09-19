# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

All common tasks are run via `task` (Taskfile). Run from the repo root.

### Backend

```bash
task backend:install          # uv sync --group dev
task backend:dev              # FastAPI on :8000 with --reload
task backend:worker           # Temporal worker process
task backend:test             # pytest backend/tests
task backend:lint             # ruff check
task backend:format           # ruff format
task backend:migrate          # alembic upgrade head
task backend:migrate:new -- -m "description"  # autogenerate new migration
```

Run a single test file or test:
```bash
uv run --project backend pytest backend/tests/test_health.py
uv run --project backend pytest backend/tests/test_ai_tasks.py::test_submit_task
```

### Frontend

```bash
task frontend:install         # npm install
task frontend:dev             # Vite dev server on :3000
task frontend:build           # production build
```

### Infrastructure

```bash
task docker:up                # full stack (Postgres, Temporal, MinIO, Langfuse, Ollama, API)
task db:up                    # only Postgres
```

## Architecture

### Overview

Monorepo with three layers: `frontend/` (React), `backend/` (FastAPI + Temporal worker), `docker-compose.yml` (local stack).

### Backend (`backend/src/hargus_api/`)

**Settings** — `config.py` uses Pydantic `BaseSettings` with `HARGUS_` env prefix. All settings loaded via `get_settings()` (LRU-cached). Copy `backend/.env.example` to `backend/.env` to configure locally.

**API layer** — `api/routes/` contains one file per domain (vacancies, candidates, ai_tasks, background, health). All responses use Pydantic `Field(alias=...)` camelCase, serialized with `by_alias=True`.

**Service layer** — `services/ai_task_service.py` is the only stateful service. It holds a module-level repository cache (`_POSTGRES_REPOSITORIES`) and a cached Temporal client. `AiTaskService.__init__` tries `PostgresAiTaskRepository` first; falls back to `InMemoryAiTaskRepository` silently (allows tests without a live DB).

**Repository layer** — `repositories/` has the in-memory and psycopg-backed implementations. `db/repositories/` has async SQLAlchemy repos for `WorkflowRun` and `AnalysisReport`. Note: `PostgresAiTaskRepository` uses sync `psycopg.connect` and requires a plain `postgresql://` URL (the service strips `+asyncpg` before passing it).

**Database** — `db/models.py` defines three tables: `workflow_runs`, `analysis_reports`, `document_chunks` (with a 768-dim pgvector column for `nomic-embed-text` embeddings). Migrations are async Alembic (`db/migrations/env.py` uses `asyncio.run()`). When adding models, import them in `env.py` so autogenerate picks them up.

**Temporal workflow** — `temporal/workflows/candidate_analysis.py` defines `CandidateAnalysisWorkflow`. Phase structure:
1. `load_documents_activity` → `parse_documents_activity` (sequential, IO-bound)
2. `chunk_and_embed_activity` (pgvector storage)
3. `run_jd_analysis_activity`, `run_candidate_extraction_activity`, `run_interview_insight_activity`, `run_consistency_check_activity` (parallel, LLM-bound)
4. `consolidate_facts_activity` → `score_candidate_activity` (deterministic)
5. `draft_report_activity` (LLM)
6. `render_pdf_activity` (WeasyPrint + Jinja2)
7. `store_and_notify_activity` (persists `AnalysisReport`, uploads PDF)

The workflow is only launched when `HARGUS_TEMPORAL_ENABLED=true`. Without it, `AiTaskService.submit_task` records a task in memory with `status=queued` and returns immediately.

**Worker registration** — `worker.py` registers all 13 activities and 2 workflows. When adding an activity, it must be registered here.

**Storage abstraction** — `storage/` provides `LocalStorage` and `S3Storage` behind a common interface. Selected by `HARGUS_STORAGE_BACKEND`.

### Frontend (`frontend/src/`)

**API client** — `lib/api.ts` is the single typed fetch client. `BASE` comes from `VITE_API_URL` (defaults to `http://localhost:8000/api/v1`). All pages import from here — no page makes `fetch` calls directly.

**Demo mode** — `lib/mode.ts` exports `isDemoMode`. Set `VITE_MODE=DEMO` in `frontend/.env` to enable static mock data from `data/mock.ts`. Pages always fetch from the API when demo mode is off; `data/mock.ts` is only used by demo mode.

**Page data flow** — every page uses the same pattern: `useState([])` + `useEffect` calling `api.*` + loading spinner while `loading=true`. No global state manager.

**AI task polling** — `CandidateDetailPage` submits to `POST /api/v1/ai/tasks` then polls `GET /api/v1/ai/tasks/{id}` every 2s for up to 8 attempts (16s). If still not `completed`, shows a "queued" message.

### Analysis config

`ai/config.py` exports `get_analysis_prompt()`, `get_rag_k()`, `get_chunk_size()`, `get_chunk_overlap()`. Resolution order for the prompt: YAML file (`analysis_config.yml` in the package root, optional) → `HARGUS_ANALYSIS_PROMPT` env var → hardcoded default. The YAML file is not checked in; create one locally to override the prompt without code changes.

### Key wiring details

- Alembic URL comes from `get_settings()` at import time in `env.py` — `HARGUS_DATABASE_URL` must be set before running migrations.
- `DocumentChunk.embedding` is `Vector(768)` — changing embedding models requires a new migration.
- Frontend CORS origin is `HARGUS_FRONTEND_ORIGIN` (default `http://localhost:3000`).
- Temporal task queue name must match between API (`HARGUS_TEMPORAL_TASK_QUEUE`) and worker.
- Python packages: all subdirectories under `src/hargus_api/` must have an `__init__.py`. Alembic dirs (`db/migrations/`, `db/migrations/versions/`) and `pdf/templates/` are not Python packages and have none.
- `build_json_chain` in `ai/agents/base.py` uses `SystemMessage` (not the `("system", template)` tuple) for the system prompt to prevent LangChain from parsing JSON examples in the prompt as f-string template variables.
- Agent tests use a `_FixedResponseLLM(BaseChatModel)` subclass (in `tests/test_agents.py`) — not a `MagicMock` — because LangChain's chain composition requires `_generate` to be implemented.
- Synthetic candidate generator: `python -m tests.synthetic.generate_candidates --count 20 --out candidates.json` produces 4 tiers (strong / possible / weak / red_flag) with ground-truth labels for evaluation benchmarking.
