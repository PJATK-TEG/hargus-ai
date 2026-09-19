# API Overview

## Base URL

- Local backend: `http://localhost:8000`
- API prefix: `/api/v1`

All response shapes use camelCase JSON (Pydantic `Field(alias=...)` + FastAPI `by_alias=True`).

## Health

### `GET /api/v1/health`

Returns service metadata and whether Temporal launching is enabled.

## Vacancies

### `GET /api/v1/vacancies`

Returns all vacancies.

### `GET /api/v1/vacancies/{vacancy_id}`

Returns one vacancy or `404`.

### `GET /api/v1/vacancies/{vacancy_id}/candidates`

Returns candidates associated with the vacancy.

## Candidates

### `GET /api/v1/candidates`

Returns all candidates. Optional query param: `vacancyId` to filter by vacancy.

### `GET /api/v1/candidates/{candidate_id}`

Returns one candidate or `404`.

### `GET /api/v1/candidates/{candidate_id}/messages`

Returns AI chat / recruiter message history for the candidate.

## AI Tasks

### `POST /api/v1/ai/tasks`

Submits an AI analysis task. Always returns a task record immediately.

When `HARGUS_TEMPORAL_ENABLED=true`, starts the full `CandidateAnalysisWorkflow` in Temporal:
document loading → parsing → chunking/embedding → 4 parallel LangGraph agents → scoring → PDF report → Postgres persistence.

When Temporal is disabled, records the task in memory with a stub result.

Example body:

```json
{
  "type": "candidate_summary",
  "candidateId": "c1",
  "prompt": "Summarize this candidate for the backend role."
}
```

Supported `type` values: `candidate_summary`, `candidate_comparison`, `candidate_red_flags`, `candidate_background_check`

### `GET /api/v1/ai/tasks/{task_id}`

Returns one AI task or `404`. Poll this endpoint to track workflow progress.

## Background Checks

### `GET /api/v1/background/sources`

Returns available background check data sources.

### `POST /api/v1/background/checks`

Submits a background check request.

### `GET /api/v1/background/checks/{check_id}`

Returns one background check result or `404`.

### `POST /api/v1/background/sources/{source}/search`

Searches a specific background check source.

## Frontend Integration

The React frontend uses `src/lib/api.ts` as a typed fetch client against these endpoints.

When `VITE_MODE=DEMO` the frontend skips all API calls and uses static mock data instead.
When `VITE_MODE` is unset the frontend makes real calls to `VITE_API_URL` (defaults to `http://localhost:8000/api/v1`).
