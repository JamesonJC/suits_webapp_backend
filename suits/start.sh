#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# start.sh — Render Native Python Start Script
#
# Render calls this to start the web service after build.sh completes.
# The database IS available at this point, so migrations run safely here.
#
# RENDER DASHBOARD SETTINGS (Native Python):
#   Start Command: bash start.sh
# ─────────────────────────────────────────────────────────────────────────────

set -o errexit

echo ""
echo "╔══════════════════════════════════════════════╗"
echo "║     Suits Backend — Startup Phase            ║"
echo "╚══════════════════════════════════════════════╝"
echo ""

# ── Step 1: Apply database migrations ─────────────────────────────────────────
# Safe to run on every deploy — Django skips already-applied migrations.
# This ensures every new migration (including the Task model 0002_task) runs.
echo "  Running database migrations..."
python manage.py migrate --noinput
echo " Migrations complete."
echo ""

# ── Step 2: Start Gunicorn ────────────────────────────────────────────────────
PORT="${PORT:-8000}"
echo "  Starting Gunicorn on port ${PORT}..."

exec gunicorn config.wsgi:application \
    --bind "0.0.0.0:${PORT}" \
    --workers "${GUNICORN_WORKERS:-2}" \
    --timeout "${GUNICORN_TIMEOUT:-120}" \
    --access-logfile - \
    --error-logfile  - \
    --log-level info