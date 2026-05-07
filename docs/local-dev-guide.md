# Local Development Guide

## Prerequisites

- **Docker Desktop** running
- **`task` CLI** — [taskfile.dev/installation](https://taskfile.dev/installation/) (`choco install go-task` on Windows)
- **`uv`** — Python package manager (`pip install uv`)

---

## Step 1 — Start infrastructure

```bash
docker compose up -d postgres temporal temporal-ui langfuse minio
```

Wait ~30 seconds for Temporal to finish its first-boot migrations against Postgres.

**Verify services are up:**

| Service | URL |
|---------|-----|
| Temporal UI | http://localhost:8080 |
| Langfuse | http://localhost:3001 |
| MinIO console | http://localhost:9001 (user: `minioadmin`, pass: `minioadmin`) |
| Ollama | http://localhost:11434 |

---

## Step 2 — Pull Ollama models

Only needed once.

```bash
ollama pull llama3.1
ollama pull nomic-embed-text
```

This may take several minutes depending on your connection.

---

## Step 3 — Configure environment

Copy the example env file and adjust as needed:

```bash
cp backend/.env.example backend/.env
```

Minimum required values for a local Ollama setup (defaults in `.env.example` already match):

```env
HARGUS_DATABASE_URL=postgresql+asyncpg://hargus:hargus@localhost:5432/hargus
HARGUS_TEMPORAL_ENABLED=true
HARGUS_TEMPORAL_SERVER_URL=localhost:7233
HARGUS_LLM_PROVIDER=ollama
HARGUS_LLM_MODEL=llama3.1
HARGUS_EMBEDDING_PROVIDER=ollama
HARGUS_EMBEDDING_MODEL=nomic-embed-text
HARGUS_OLLAMA_BASE_URL=http://localhost:11434
HARGUS_STORAGE_BACKEND=local
HARGUS_LOCAL_STORAGE_PATH=./data/files
```

---

## Step 4 — Install backend dependencies

```bash
task backend:install
```

---

## Step 5 — Run database migrations

```bash
task backend:migrate
```

This runs `alembic upgrade head`, which creates all application tables (`workflow_runs`, `analysis_reports`, `document_chunks`, `vacancies`, `candidates`, `candidate_files`, `messages`) and enables the `pgvector` extension.

**Verify:**
```bash
docker exec -it hargus-ai-postgres-1 psql -U hargus -d hargus -c "\dt"
```

You should see all application tables plus Alembic's `alembic_version` tracking table.

> **Future schema changes:** after editing `db/models.py`, generate a new migration with:
> ```bash
> task backend:migrate:new -- -m "describe_your_change"
> ```
> then apply it with `task backend:migrate`.

---

## Step 6 — Start the API and Worker

Open two terminals:

**Terminal 1 — FastAPI API:**
```bash
task backend:dev
```
API is available at http://localhost:8000
Swagger UI at http://localhost:8000/docs

**Terminal 2 — Temporal Worker:**
```bash
task backend:worker
```

The worker must be running or submitted workflows will stay queued in Temporal indefinitely.

---

## Step 7 — Trigger a candidate analysis

Use Swagger at http://localhost:8000/docs or curl:

```bash
curl -X POST http://localhost:8000/api/v1/ai/tasks \
  -H "Content-Type: application/json" \
  -d '{
    "type": "candidate_summary",
    "candidateId": "c1",
    "vacancyId": "v1"
  }'
```

Response:
```json
{
  "id": "<task-uuid>",
  "type": "candidate_analysis",
  "status": "running",
  ...
}
```

---

## Step 8 — Watch the workflow execute

**Temporal UI** → http://localhost:8080
Navigate to `default` namespace → **Workflows** → find `analysis-<uuid>` → watch activities complete step by step.

**Worker terminal** — activity logs scroll as each phase runs:
```
load_documents: candidate=candidate-001 loaded=0 docs
parse_documents: run=... parsed=0/0
chunk_and_embed: ...
run_jd_analysis_activity completed
run_candidate_extraction_activity completed
...
store_and_notify: completed workflow run analysis-...
```

---

## Step 9 — Verify results in the database

```bash
# Check workflow run status
docker exec -it hargus-ai-postgres-1 psql -U hargus -d hargus \
  -c "SELECT id, status, completed_at FROM workflow_runs ORDER BY started_at DESC LIMIT 5;"

# Check analysis report
docker exec -it hargus-ai-postgres-1 psql -U hargus -d hargus \
  -c "SELECT candidate_id, vacancy_id, overall_score, recommendation FROM analysis_reports LIMIT 5;"
```

---

## Known stubs (expected behavior)

The following are placeholders pending DB wiring in the next iteration:

| Stub | Effect |
|------|--------|
| `_list_candidate_keys()` returns `[]` | No documents loaded; agents run on empty text |
| `_vacancy_description()` returns placeholder | JD agent receives a fake description, not a real job spec |

The full pipeline still executes end-to-end and the report is persisted to the DB — the LLM output will just be minimal without real input documents.

---

## Optional — Enable Langfuse tracing

1. Open http://localhost:3001 and create a local account
2. Create a project and copy the API keys
3. Update `backend/.env`:
   ```env
   HARGUS_LANGFUSE_ENABLED=true
   HARGUS_LANGFUSE_HOST=http://localhost:3001
   HARGUS_LANGFUSE_PUBLIC_KEY=pk-lf-...
   HARGUS_LANGFUSE_SECRET_KEY=sk-lf-...
   ```
4. Restart the API and worker — all LLM calls will be traced in Langfuse

---

## Useful task commands

```bash
task backend:dev              # Start FastAPI (hot reload)
task backend:worker           # Start Temporal worker
task backend:migrate          # Apply migrations (alembic upgrade head)
task backend:migrate:new      # Generate a new migration (add -- -m "name")
task backend:test             # Run tests
task backend:lint             # Lint with ruff
task backend:format           # Format with ruff
task docker:up                # Full docker compose up --build
task docker:down              # Stop all containers
```
