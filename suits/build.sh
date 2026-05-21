#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# build.sh — Render Native Python Build Script
#
# Used when deploying WITHOUT Docker (Render "Python" runtime).
# Render calls this automatically every time you push to main.
#
# RENDER DASHBOARD SETTINGS (Native Python):
#   Root Directory  : suits
#   Build Command   : bash build.sh
#   Start Command   : bash start.sh
#
# NOTE: If you're using Docker (recommended), Render uses Dockerfile +
#       entrypoint.sh instead. This file is the alternative for native Python.
# ─────────────────────────────────────────────────────────────────────────────

# Exit immediately on any error — Render will mark the build as failed
# and NOT deploy the broken version. This protects production.
set -o errexit

echo ""
echo "╔══════════════════════════════════════════════╗"
echo "║     Suits Backend — Build Phase              ║"
echo "╚══════════════════════════════════════════════╝"
echo ""

# ── Step 1: Install Python dependencies ───────────────────────────────────────
echo "  Installing Python packages..."
pip install --upgrade pip
pip install -r requirements.txt
echo " Packages installed."
echo ""

# ── Step 2: Collect static files ──────────────────────────────────────────────
# WHY --clear: removes old files before collecting so stale assets don't linger
# WHY --noinput: suppresses the confirmation prompt for automated builds
# Static files go to STATIC_ROOT (staticfiles/) and are served by WhiteNoise
echo " Collecting static files..."
python manage.py collectstatic --noinput --clear
echo " Static files collected."
echo ""

echo "╔══════════════════════════════════════════════╗"
echo "║     Build complete                          ║"
echo "╚══════════════════════════════════════════════╝"
echo ""
echo "NOTE: Migrations run in start.sh (not here)"
echo "      because the database is not available"
echo "      during the build phase on Render."