# syntax=docker/dockerfile:1
#
# Standalone ASGI image for the Sillas Rotary API (Issue #84).
#
# Runs the exact same backend/main.py FastAPI app that Vercel serves through
# api/index.py, but via a plain uvicorn process — no serverless shim, so this
# image runs unmodified on any container runtime (App Runner, Cloud Run,
# ECS, plain `docker run`, ...). Vercel keeps working in parallel; nothing
# here changes api/index.py or vercel.json.
#
# Secrets (DB_*, SUPABASE_*, JWT_SECRET, ...) are never baked into the image —
# pass them at `docker run` time via `-e` / `--env-file` (see README.md).

FROM python:3.12-slim

WORKDIR /app

# ca-certificates: required for HTTPS calls this process makes at runtime
# (Supabase Storage, Resend).
RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ backend/
COPY front/ front/

# main.py resolves the frontend dir relative to itself (../front), so the
# working directory must be backend/ — same layout start.sh uses locally.
WORKDIR /app/backend

ENV PYTHONUNBUFFERED=1 \
    PORT=8080

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
    CMD python3 -c "import urllib.request; urllib.request.urlopen('http://localhost:${PORT}/api/health', timeout=2)" || exit 1

# Shell form so $PORT expands — container runtimes like Cloud Run/App Runner
# inject PORT and expect the process to bind to it.
CMD uvicorn main:app --host 0.0.0.0 --port ${PORT}
