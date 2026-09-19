FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    libgobject-2.0-0 \
    libpango-1.0-0 \
    libpangoft2-1.0-0 \
    libpangocairo-1.0-0 \
    libcairo2 \
    libgdk-pixbuf-2.0-0 \
    libffi-dev \
    shared-mime-info \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app/backend

RUN pip install --no-cache-dir uv

# Copy dependency manifests first — layer is only invalidated when these change
COPY backend/pyproject.toml backend/uv.lock backend/README.md /app/backend/

# Stub the package so uv can resolve and install all dependencies
RUN mkdir -p src/hargus_api && touch src/hargus_api/__init__.py
RUN uv pip install --system -e .

# Copy real source (overwrites the stub)
COPY backend/src /app/backend/src

CMD ["uvicorn", "hargus_api.main:app", "--app-dir", "src", "--host", "0.0.0.0", "--port", "8000"]
