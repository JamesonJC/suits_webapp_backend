#!/bin/bash
# ─────────────────────────────────────────────────────────────────────────────
# entrypoint.sh — container startup script
#
# Runs every time Render deploys a new container (after the Docker image is
# built). The database IS available here, so migrations are safe to run.
#
# EXECUTION ORDER:
#   1. Wait briefly if DB might still be starting (defensive)
#   2. Run all pending database migrations
#   3. Start Gunicorn
#
# WHY MIGRATIONS HERE (not in the Dockerfile):
#   During "docker build", Render builds the image in an isolated environment
#   with no network access to your database. Running migrate there would fail
#   with "could not connect to server". The entrypoint runs AFTER the container
#   starts — at that point Render has already provisioned the DB and injected
#   the DATABASE_URL, so migrations work correctly.
#
# IDEMPOTENCY:
#   "python manage.py migrate" is safe to run on every deploy.
#   Django tracks which migrations have already run in the django_migrations
#   table. It skips already-applied migrations and only applies new ones.
# ─────────────────────────────────────────────────────────────────────────────

set -e  # Exit immediately if any command fails

echo ""
echo "╔══════════════════════════════════════════════╗"
echo "║     Suits Backend — Starting Up              ║"
echo "╚══════════════════════════════════════════════╝"
echo ""

# ── Step 1: Apply all database migrations ─────────────────────────────────────
# This creates or updates tables for:
#   • Django internals (auth, sessions, contenttypes, admin)
#   • All apps: tenants, lawfirms, users, workflows, jobs (including Task), etc.
# New migrations added in this session: 0002_task (Task model)
echo "  Running database migrations..."
python manage.py migrate --noinput
echo " Migrations complete."
echo ""

# ── Step 2: Start Gunicorn ────────────────────────────────────────────────────
# Configuration:
#   --bind         : Listen on all interfaces at the port Render assigns ($PORT)
#   --workers      : 2 workers fit comfortably in Render's free 512 MB RAM
#                    Rule of thumb: 2 × CPU + 1, but free tier has 1 shared CPU
#   --timeout      : 120 s — Render free tier can have slow cold starts
#   --access-logfile - : Write access logs to stdout (Render captures these)
#   --error-logfile -  : Write error logs to stderr
#   --log-level    : "info" shows request lines without being too verbose

PORT="${PORT:-8000}"  # Render always sets PORT; fall back to 8000 for local Docker

echo "▶  Starting Gunicorn on port ${PORT}..."
exec gunicorn config.wsgi:application \
    --bind "0.0.0.0:${PORT}" \
    --workers "${GUNICORN_WORKERS:-2}" \
    --timeout "${GUNICORN_TIMEOUT:-120}" \
    --access-logfile - \
    --error-logfile  - \
    --log-level info