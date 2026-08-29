FROM python:3.12-slim AS builder

WORKDIR /build

# Install uv for fast, reproducible dependency resolution.
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Sync dependencies from the lockfile into a virtual environment.
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

# Copy application code so uv can install the project itself.
COPY app/ app/
RUN uv sync --frozen --no-dev


# ---------------------------------------------------------------------------
FROM python:3.12-slim AS runtime

WORKDIR /app

# curl is needed for the Docker health check.
RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

# Copy the virtual environment from the builder.
COPY --from=builder /build/.venv /app/.venv
ENV PATH="/app/.venv/bin:$PATH"

# Copy application code + Alembic config.
COPY app/ app/
COPY alembic/ alembic/
COPY alembic.ini .

EXPOSE 8000

# Run migrations then start the server.
CMD ["sh", "-c", "python -m alembic upgrade head && python -m uvicorn app.main:app --host 0.0.0.0 --port 8000"]
