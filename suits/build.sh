#!/usr/bin/env bash
# suits/build.sh
#
# Render runs this script automatically on every deploy, BEFORE
# starting the web server. Think of it as your deployment checklist.
#
# Steps:
#   1. Upgrade pip (always good practice)
#   2. Install all Python dependencies from requirements.txt
#   3. Run database migrations (applies any new migrations to Postgres)
#   4. Collect static files (copies admin CSS etc. into staticfiles/)

set -o errexit  # exit immediately if any command fails

echo "▶ Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

echo "▶ Running migrations..."
python manage.py migrate --noinput

echo "▶ Collecting static files..."
python manage.py collectstatic --noinput --clear

echo " Buid complete."