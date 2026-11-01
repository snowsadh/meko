# ── Stage 1: Build virtualenv ──────────────────────────────────────────────
FROM python:3.12-slim AS builder

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

COPY pyproject.toml uv.lock ./
RUN uv sync --no-install-project --no-dev

# ── Stage 2: Runtime ────────────────────────────────────────────────────────
FROM python:3.12-slim

RUN apt-get update -qq \
 && apt-get install -y -qq --no-install-recommends fonts-dejavu-core git curl ca-certificates \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY --from=builder /app/.venv /app/.venv
ENV PATH="/app/.venv/bin:$PATH"

COPY app     /app/app
COPY alembic /app/alembic
COPY alembic.ini /app/

ENV PYTHONUNBUFFERED=1

CMD ["sh", "-c", "migrated=false; for attempt in $(seq 1 30); do if alembic upgrade head; then migrated=true; break; fi; echo \"Alembic waiting for database (attempt $attempt/30)\"; sleep 2; done; test \"$migrated\" = true || exit 1; exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --no-access-log"]
