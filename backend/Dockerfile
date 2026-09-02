# ─── Stage 1: Builder — install dependencies ──────────────────
FROM python:3.13-slim AS builder

WORKDIR /app

# Install build deps for C extensions, then install to a target dir
# (no need to keep build tools in the final image)
RUN apt-get update \
    && apt-get install -y --no-install-recommends gcc \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir --upgrade pip

# Install all deps to /install so we can copy only that in stage 2
COPY requirements.txt .
RUN pip install --no-cache-dir --target=/install -r requirements.txt "uvicorn[standard]"

# ─── Stage 2: Runtime — slim final image ───────────────────────
FROM python:3.13-slim

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /install /usr/local/lib/python3.13/site-packages

# Copy console scripts (uvicorn, gunicorn, django-admin, etc.) so they are on PATH
COPY --from=builder /install/bin/* /usr/local/bin/

# Create non-root runtime user for security
RUN groupadd -r apitest && useradd -r -g apitest -d /app -s /sbin/nologin apitest

# Create SQLite data directory and make it writable by the runtime user
RUN mkdir -p /app/data /app/logs && chown -R apitest:apitest /app

# Copy application code (after dependency installation to leverage layer cache)
COPY --chown=apitest:apitest . .

# Make entrypoint executable
RUN chmod +x entrypoint.sh

ENV DATABASE_PATH=/app/data/db.sqlite3
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

EXPOSE 8000

USER apitest

ENTRYPOINT ["./entrypoint.sh"]
