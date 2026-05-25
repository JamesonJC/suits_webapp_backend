#!/bin/bash
# ─────────────────────────────────────────────────────────────────────────────
# entrypoint.sh
#
# Runs inside the container every time Render starts or redeploys the service.
# At this point the PostgreSQL database IS available — migrations are safe.
#
# ORDER:
#   1. Run ALL pending migrations (creates/updates tables)
#   2. Start Gunicorn
#
# SAFETY: `migrate --noinput` is fully idempotent — it checks the
# django_migrations table and skips anything already applied.
# It is safe to run on every single deploy.
# ─────────────────────────────────────────────────────────────────────────────
set -e

echo "======================================================"
echo "  Suits Backend — Container Starting"
echo "======================================================"
echo ""

echo " Applying database migrations..."
python manage.py migrate --noinput
echo " Migrations complete."
echo ""

PORT="${PORT:-8080}"
echo "  Starting Gunicorn on port ${PORT}..."
exec gunicorn config.wsgi:application \
    --bind "0.0.0.0:${PORT}" \
    --workers 2 \
    --timeout 120 \
    --access-logfile - \
    --error-logfile - \
    --log-level info