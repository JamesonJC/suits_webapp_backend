# ─────────────────────────────────────────────────────────────────────────────
# Dockerfile  — suits_webapp_backend/suits/Dockerfile
#
# HOW RENDER USES THIS FILE:
#   1. "docker build" runs every time you push to main.
#      The build context is the suits/ directory.
#      At this stage the DATABASE is NOT available — migrations cannot run here.
#
#   2. "docker run" starts the container after the image is built.
#      The DATABASE IS available — entrypoint.sh runs migrations here.
#
# TWO-STAGE BUILD:
#   Stage 1 (builder) — install Python deps into a virtual env.
#   Stage 2 (runtime) — copy only the venv + source, discard build tools.
#   This keeps the final image small (~200 MB vs ~500 MB single-stage).
# ─────────────────────────────────────────────────────────────────────────────

# ── Stage 1: builder ──────────────────────────────────────────────────────────
FROM python:3.12-slim AS builder

# Prevents .pyc files and enables stdout/stderr logs immediately in Render
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install build-time OS deps (needed to compile psycopg2 if binary fails)
RUN apt-get update \
    && apt-get install -y --no-install-recommends gcc libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first — Docker layer-caches this step.
# Re-runs ONLY when requirements.txt changes, not on every code push.
COPY requirements.txt .

# Install into an isolated virtualenv so stage 2 can copy just /venv
RUN python -m venv /venv \
    && /venv/bin/pip install --upgrade pip \
    && /venv/bin/pip install --no-cache-dir -r requirements.txt

# ── Stage 2: runtime ──────────────────────────────────────────────────────────
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/venv/bin:$PATH"

WORKDIR /app

# Only runtime OS deps — no gcc or build tools needed here
RUN apt-get update \
    && apt-get install -y --no-install-recommends libpq5 \
    && rm -rf /var/lib/apt/lists/*

# Copy the virtualenv from builder (all installed packages)
COPY --from=builder /venv /venv

# Copy the Django project source code
COPY . .

# ── Collect static files at BUILD time ────────────────────────────────────────
# WHY at build time:
#   collectstatic only reads the file system — it does NOT need a database.
#   Running it here means every running container already has static files ready.
#
# WHY the dummy SECRET_KEY:
#   Django refuses to start with the default insecure key when DEBUG=False.
#   We pass a real-looking but throwaway key just for this one command.
#   The actual SECRET_KEY is injected at runtime via Render's environment vars.
#
# WHY --noinput:
#   Suppresses the "Are you sure?" prompt — needed for automated builds.
RUN SECRET_KEY="build-time-placeholder-not-used-in-production" \
    DEBUG="False" \
    DATABASE_URL="" \
    python manage.py collectstatic --noinput --clear

# Expose the port Render will route traffic to.
# Render sets the $PORT env var at runtime; entrypoint.sh reads it.
EXPOSE 8000

# Copy and make executable the startup script.
# entrypoint.sh runs migrations THEN starts Gunicorn.
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# This runs when the container starts (not at build time).
ENTRYPOINT ["/entrypoint.sh"]