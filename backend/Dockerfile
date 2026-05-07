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

COPY backend /app/backend
RUN pip install --no-cache-dir uv && uv pip install --system .

CMD ["uvicorn", "hargus_api.main:app", "--app-dir", "src", "--host", "0.0.0.0", "--port", "8000"]
