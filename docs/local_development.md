# Local Development

> **This document is superseded by [`local-dev-guide.md`](./local-dev-guide.md)**, which contains the full, up-to-date setup walkthrough including Docker infrastructure, Alembic migrations, Ollama model setup, and end-to-end flow verification.

## Quick Reference

```bash
# Infrastructure
task docker:up

# Backend
task backend:install
task backend:migrate
task backend:dev       # API on :8000
task backend:worker    # Temporal worker

# Frontend
task frontend:dev      # Dev server on :3000
```

Frontend demo mode (no backend required):

```bash
# frontend/.env
VITE_MODE=DEMO
```

Frontend live mode:

```bash
# frontend/.env
VITE_API_URL=http://localhost:8000/api/v1
# (leave VITE_MODE unset)
```
