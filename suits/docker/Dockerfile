# suits/docker/Dockerfile
#
# ─────────────────────────────────────────────────────────────────────────────
# WHAT WAS BROKEN — WHY /api/tasks/ RETURNED 500 ON EVERY REQUEST:
#
#   1. OLD CMD: CMD ["gunicorn", "config.wsgi:application", ...]
#      Gunicorn started immediately with ZERO migration steps.
#      The tasks_task table never existed in the database.
#      PostgreSQL: "relation tasks_task does not exist" → HTTP 500.
#
#   2. 0002_task.py was missing from the repo — the Task model had no
#      migration file, so `migrate` would have skipped creating the table
#      even if it had run.
#
# WHAT IS FIXED:
#    entrypoint.sh replaces the direct CMD.
#      It runs `python manage.py migrate --noinput` BEFORE gunicorn starts.
#      Migrations are now GUARANTEED to run on every single deploy.
#
#    0002_task.py added to suits/apps/jobs/migrations/
#      Creates tasks_task with all required columns.
#
# RENDER BUILD FLOW:
#   docker build  (this file) → installs packages, collects static
#   docker run    (entrypoint.sh)  → migrates DB, starts gunicorn
#
# NOTE ON COPY PATHS:
#   Render sets the build context to suits/docker/ (where this Dockerfile lives).
#   COPY ../requirements.txt  → copies suits/requirements.txt  ✓
#   COPY ../                  → copies the entire suits/ tree   ✓
#   COPY entrypoint.sh        → copies suits/docker/entrypoint.sh ✓
#   All paths are relative to the build context (suits/docker/).
# ─────────────────────────────────────────────────────────────────────────────

FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# System libraries needed to compile psycopg2
RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# ── Python dependencies ───────────────────────────────────────────────────────
# Copy requirements.txt first so Docker can cache the install layer.
# This layer only rebuilds when requirements.txt changes — not on every push.
COPY ../requirements.txt .
RUN pip install --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# ── Application source code ───────────────────────────────────────────────────
# Copies the full suits/ directory (parent of build context) into /app
COPY ../ .

# ── Static files ──────────────────────────────────────────────────────────────
# collectstatic reads the filesystem only — no database needed.
# Uses a throwaway SECRET_KEY because Django won't run without one.
# The real SECRET_KEY is injected at runtime via Render environment variables.
RUN SECRET_KEY="build-time-placeholder-replace-at-runtime" \
    DEBUG="False" \
    DATABASE_URL="" \
    python manage.py collectstatic --noinput

# ── Entrypoint ────────────────────────────────────────────────────────────────
# entrypoint.sh lives in the same directory as this Dockerfile (suits/docker/).
# COPY entrypoint.sh → looks in the build context (suits/docker/) → found ✓
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

EXPOSE 8080

# THE KEY FIX:
# Old: CMD ["gunicorn", ...] — jumped straight to serving, skipped migrations.
# New: ENTRYPOINT calls entrypoint.sh which runs:
#        python manage.py migrate --noinput   ← ALL migrations applied here
#        gunicorn config.wsgi:application     ← server starts after DB is ready
ENTRYPOINT ["/entrypoint.sh"]
