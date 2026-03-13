# Suits Backend — Fly.io Deployment Guide

> Step-by-step guide to deploy the Django backend to Fly.io with PostgreSQL,
> GitHub Actions CI/CD, and full React frontend readiness.
>
> **Stack:** Django 6.0.2 · DRF · PostgreSQL · Cloudflare R2 · JWT Auth · Fly.io

---

## Overview of What We're Setting Up

```
GitHub (push to main)
    ↓
GitHub Actions (run tests → deploy)
    ↓
Fly.io (runs Django + Gunicorn)
    ↓
Fly Postgres (your database)
    ↓
Cloudflare R2 (file storage)
```

React frontend connects to your Fly.io URL via the REST API.

---

## PART 1 — Production Settings

Right now `config/settings.py` has `DEBUG = True` and a hardcoded `SECRET_KEY`.
We need to split settings into dev and production safely.

### Step 1.1 — Install python-decouple

This lets us read secrets from environment variables (Fly.io secrets) without
touching the code.

```bash
pip install python-decouple
pip freeze > requirements.txt
```

### Step 1.2 — Update config/settings.py

Replace the top of your `config/settings.py` with this. The comments explain
every change and why it matters.

```python
# config/settings.py

from pathlib import Path
from datetime import timedelta
import os
from decouple import config, Csv  # reads from env vars or .env file

BASE_DIR = Path(__file__).resolve().parent.parent

# ─── Security ────────────────────────────────────────────────────────────────
# SECRET_KEY: In dev, falls back to the insecure default.
# In production (Fly.io), this MUST be set as a secret — never hardcode it.
SECRET_KEY = config("SECRET_KEY", default="django-insecure-change-me-in-production")

# DEBUG: False in production. Fly.io sets DEBUG=False automatically.
# Never run with DEBUG=True on a public server — it exposes your full stack trace.
DEBUG = config("DEBUG", default=False, cast=bool)

# ALLOWED_HOSTS: Which domain names Django will respond to.
# In production this must be your Fly.io domain (e.g. suits.fly.dev).
# Csv() lets you pass multiple hosts as a comma-separated string.
ALLOWED_HOSTS = config("ALLOWED_HOSTS", default="localhost,127.0.0.1", cast=Csv())

# ─── Apps ────────────────────────────────────────────────────────────────────
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django_filters',
    'rest_framework',
    'corsheaders',
    'apps.core',
    'apps.tenants',
    'apps.lawfirms',
    'apps.users',
    'apps.rbac',
    'apps.forms_engine',
    'apps.jobs',
    'apps.api',
    'apps.workflows',
    'apps.audit',
]

# ─── Middleware ───────────────────────────────────────────────────────────────
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",  # serves static files in production
    "django.contrib.sessions.middleware.SessionMiddleware",
    "corsheaders.middleware.CorsMiddleware",       # must be before CommonMiddleware
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "apps.tenants.middleware.TenantMiddleware",
    "apps.audit.middleware.AuditMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

# ─── REST Framework ───────────────────────────────────────────────────────────
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework.authentication.SessionAuthentication",
        "rest_framework.authentication.BasicAuthentication",
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": (
        "rest_framework.permissions.IsAuthenticated",
    ),
    "DEFAULT_FILTER_BACKENDS": (
        "django_filters.rest_framework.DjangoFilterBackend",
    ),
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=30),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
}

# ─── CORS (Cross-Origin Resource Sharing) ────────────────────────────────────
# This controls which domains can call your API from a browser.
# Your React frontend domain goes here.
# CORS_ALLOWED_ORIGINS is read from env so you can change it without redeploying.
CORS_ALLOWED_ORIGINS = config(
    "CORS_ALLOWED_ORIGINS",
    default="http://localhost:3000,http://localhost:5173",  # Vite + CRA defaults
    cast=Csv()
)

# Allow the React frontend to send the X-Tenant-Code header with every request
CORS_ALLOW_HEADERS = [
    "accept",
    "accept-encoding",
    "authorization",
    "content-type",
    "dnt",
    "origin",
    "user-agent",
    "x-csrftoken",
    "x-requested-with",
    "x-tenant-code",   # ← your custom multi-tenant header
]

# ─── Database ─────────────────────────────────────────────────────────────────
# In development: SQLite (simple, no setup needed).
# In production (Fly.io): PostgreSQL, connection string from DATABASE_URL env var.
DATABASE_URL = config("DATABASE_URL", default=None)

if DATABASE_URL:
    # Production: parse the Fly.io Postgres connection string automatically
    import dj_database_url
    DATABASES = {
        "default": dj_database_url.parse(DATABASE_URL, conn_max_age=600)
    }
else:
    # Development: SQLite
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }

# ─── Cloudflare R2 Storage ────────────────────────────────────────────────────
CLOUDFLARE_R2_KEY_ID     = config("CLOUDFLARE_R2_KEY_ID",     default="")
CLOUDFLARE_R2_SECRET_KEY = config("CLOUDFLARE_R2_SECRET_KEY", default="")
CLOUDFLARE_R2_BUCKET     = config("CLOUDFLARE_R2_BUCKET",     default="")
CLOUDFLARE_R2_ACCOUNT_ID = config("CLOUDFLARE_R2_ACCOUNT_ID", default="")

# ─── Static Files ─────────────────────────────────────────────────────────────
# WhiteNoise serves static files directly from Gunicorn — no Nginx needed.
STATIC_URL  = "/static/"
STATIC_ROOT = os.path.join(BASE_DIR, "staticfiles")
STATICFILES_DIRS = [os.path.join(BASE_DIR, "static")] if os.path.exists(os.path.join(BASE_DIR, "static")) else []
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

# ─── Auth ─────────────────────────────────────────────────────────────────────
AUTH_USER_MODEL = "users.User"

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE     = "UTC"
USE_I18N      = True
USE_TZ        = True

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
```

### Step 1.3 — Install new dependencies

```bash
pip install whitenoise dj-database-url
pip freeze > requirements.txt
```

- **whitenoise**: serves your Django static files (admin CSS, etc.) without needing a separate web server
- **dj-database-url**: parses the `DATABASE_URL` connection string Fly.io gives you

### Step 1.4 — Create a .env file for local development

Create a file called `.env` in the `suits/` directory (same level as `manage.py`).
This is already in your `.gitignore` — it will never be committed.

```bash
# suits/.env  ← never commit this file

SECRET_KEY=any-random-string-for-local-dev
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# Leave these blank for local dev — R2 only used in production
CLOUDFLARE_R2_KEY_ID=
CLOUDFLARE_R2_SECRET_KEY=
CLOUDFLARE_R2_BUCKET=
CLOUDFLARE_R2_ACCOUNT_ID=
```

Test it works:
```bash
python manage.py check
python manage.py runserver
```

---

## PART 2 — Fly.io Setup

### Step 2.1 — Install the Fly CLI

```bash
# macOS
brew install flyctl

# Linux / Windows WSL
curl -L https://fly.io/install.sh | sh
```

Log in:
```bash
fly auth login
```

### Step 2.2 — Review fly.toml

Your `fly.toml` is already set up. Here is the final version with a few
important additions explained:

```toml
# fly.toml
app            = 'suits'
primary_region = 'sin'           # Singapore — change to your closest region
console_command = '/code/manage.py shell'

[build]

[deploy]
  # Runs database migrations automatically on every deploy BEFORE traffic switches.
  # This means your DB is always up to date before new code goes live.
  release_command = 'python manage.py migrate --noinput'

[env]
  PORT = '8000'
  # These non-secret env vars can live here.
  # SECRET values (passwords, keys) go in fly secrets — never in this file.
  DJANGO_SETTINGS_MODULE = 'config.settings'

[http_service]
  internal_port      = 8000
  force_https        = true        # always redirect HTTP → HTTPS
  auto_stop_machines = 'stop'      # scale to zero when no traffic (saves money)
  auto_start_machines = true       # wake up automatically on new request
  min_machines_running = 0
  processes          = ['app']

  # Health check — Fly.io pings this to confirm the app started correctly
  [[http_service.checks]]
    grace_period  = "10s"
    interval      = "30s"
    method        = "GET"
    timeout       = "5s"
    path          = "/admin/login/"

[[vm]]
  memory = '1gb'
  cpus   = 1

[[statics]]
  guest_path = '/code/staticfiles'    # matches STATIC_ROOT in settings
  url_prefix = '/static/'
```

### Step 2.3 — Create a Fly Postgres Database

This creates a managed PostgreSQL database attached to your app.

```bash
# Create the database (free tier)
fly postgres create --name suits-db --region sin

# Attach it to your app — this automatically sets DATABASE_URL as a secret
fly postgres attach suits-db --app suits
```

After this, your app automatically has `DATABASE_URL` set. You can verify:
```bash
fly secrets list --app suits
# You should see DATABASE_URL listed
```

### Step 2.4 — Set Production Secrets on Fly.io

These are environment variables that are encrypted and injected into your
running container. Never put secrets in fly.toml or your code.

```bash
# Generate a strong secret key first (run this in your terminal)
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"

# Set all your secrets at once
fly secrets set \
  SECRET_KEY="<paste the key generated above>" \
  DEBUG="False" \
  ALLOWED_HOSTS="suits.fly.dev" \
  CORS_ALLOWED_ORIGINS="https://your-react-app.vercel.app,https://your-react-app.com" \
  CLOUDFLARE_R2_KEY_ID="<your R2 key>" \
  CLOUDFLARE_R2_SECRET_KEY="<your R2 secret>" \
  CLOUDFLARE_R2_BUCKET="<your bucket name>" \
  CLOUDFLARE_R2_ACCOUNT_ID="<your account ID>" \
  --app suits
```

> **Note:** When you set secrets, Fly.io automatically redeploys your app.

### Step 2.5 — Update the Dockerfile

Your Dockerfile needs a small update — whitenoise needs to collect static files:

```dockerfile
ARG PYTHON_VERSION=3.12-slim

FROM python:${PYTHON_VERSION}

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

RUN apt-get update && apt-get install -y \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

RUN mkdir -p /code
WORKDIR /code

COPY requirements.txt /tmp/requirements.txt
RUN pip install --upgrade pip && \
    pip install -r /tmp/requirements.txt && \
    rm -rf /root/.cache/

COPY . /code

# Collect static files (admin CSS, etc.) into staticfiles/
# SECRET_KEY is only needed here to run collectstatic — not the real production key
ENV SECRET_KEY "build-time-placeholder-not-real"
RUN python manage.py collectstatic --noinput

EXPOSE 8000

CMD ["gunicorn", "--bind", ":8000", "--workers", "2", "config.wsgi"]
```

### Step 2.6 — First Manual Deploy

```bash
cd suits   # make sure you're in the directory with fly.toml

fly deploy
```

Watch the output — you'll see it:
1. Build the Docker image
2. Run migrations (`python manage.py migrate`)
3. Start the new version
4. Switch traffic to it

Check it's running:
```bash
fly status --app suits
fly logs --app suits
```

Create your superuser:
```bash
fly ssh console --app suits
python manage.py createsuperuser
```

Your admin is now live at: `https://suits.fly.dev/admin/`

---

## PART 3 — GitHub Actions CI/CD

This sets up automatic testing and deployment every time you push to `main`.

### Step 3.1 — Get your Fly.io Deploy Token

```bash
fly tokens create deploy --app suits
```

Copy the token — you'll paste it into GitHub next.

### Step 3.2 — Add the Token to GitHub Secrets

1. Go to your GitHub repo
2. Click **Settings** → **Secrets and variables** → **Actions**
3. Click **New repository secret**
4. Name: `FLY_API_TOKEN`
5. Value: paste the token from step 3.1

### Step 3.3 — Create the GitHub Actions Workflow

Create this file in your repo. GitHub reads it automatically.

```bash
mkdir -p .github/workflows
```

```yaml
# .github/workflows/deploy.yml
#
# This workflow runs on every push to main.
# It does two things in order:
#   1. TEST  — runs your Django test suite in a clean environment
#   2. DEPLOY — if tests pass, deploys to Fly.io
#
# If tests fail, deploy is skipped. Your production app is always safe.

name: Test and Deploy

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]   # also run tests on pull requests (no deploy)

jobs:
  # ─── Job 1: Tests ──────────────────────────────────────────────────────────
  test:
    name: Run Tests
    runs-on: ubuntu-latest

    services:
      # Spin up a real PostgreSQL for tests (mirrors production)
      postgres:
        image: postgres:15
        env:
          POSTGRES_DB: suits_test
          POSTGRES_USER: suits
          POSTGRES_PASSWORD: suits
        ports:
          - 5432:5432
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5

    env:
      SECRET_KEY: "ci-test-secret-key-not-real"
      DEBUG: "True"
      ALLOWED_HOSTS: "localhost,127.0.0.1"
      DATABASE_URL: "postgresql://suits:suits@localhost:5432/suits_test"

    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.12"
          cache: "pip"

      - name: Install dependencies
        working-directory: suits
        run: |
          pip install --upgrade pip
          pip install -r requirements.txt

      - name: Run migrations
        working-directory: suits
        run: python manage.py migrate --noinput

      - name: Run tests
        working-directory: suits
        run: python manage.py test --verbosity=2

  # ─── Job 2: Deploy ──────────────────────────────────────────────────────────
  deploy:
    name: Deploy to Fly.io
    runs-on: ubuntu-latest
    needs: test                          # only run if tests passed
    if: github.ref == 'refs/heads/main'  # only deploy from main branch, not PRs

    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Set up Fly CLI
        uses: superfly/flyctl-actions/setup-flyctl@master

      - name: Deploy to Fly.io
        working-directory: suits
        run: flyctl deploy --remote-only
        env:
          FLY_API_TOKEN: ${{ secrets.FLY_API_TOKEN }}
```

### Step 3.4 — How the CI/CD Flow Works

```
You push to main
        ↓
GitHub Actions starts
        ↓
Job 1: Tests run against PostgreSQL
  ✅ Pass → Job 2 starts
  ❌ Fail → Deploy skipped, you get an email
        ↓
Job 2: fly deploy runs
  → Builds Docker image on Fly.io servers
  → Runs: python manage.py migrate
  → Starts new container
  → Switches traffic (zero downtime)
        ↓
Your app is live with the new code
```

---

## PART 4 — React Frontend Readiness

### Step 4.1 — How the React App Connects

Every API request from React needs two headers:

```javascript
// Every request must include:
headers: {
  "Authorization": `Bearer ${accessToken}`,   // JWT token from /api/auth/login/
  "X-Tenant-Code": "T1",                       // your tenant code
  "Content-Type": "application/json",
}
```

### Step 4.2 — API Base URL by Environment

```javascript
// In your React app (e.g. src/config.js)
const API_BASE_URL = process.env.REACT_APP_API_URL || "http://localhost:8000";

// Usage
const response = await fetch(`${API_BASE_URL}/api/cases/`, { headers });
```

Set the env var in your React deployment:
- **Local dev**: `REACT_APP_API_URL=http://localhost:8000`
- **Production**: `REACT_APP_API_URL=https://suits.fly.dev`

### Step 4.3 — Update CORS When You Deploy React

When you deploy the React app, come back and update the CORS secret:

```bash
fly secrets set \
  CORS_ALLOWED_ORIGINS="https://your-react-app.vercel.app" \
  --app suits
```

### Step 4.4 — Key API Endpoints for React

```
# Auth
POST   /api/auth/login/         body: {username, password}  → returns {access, refresh}
POST   /api/auth/refresh/       body: {refresh}             → returns {access}

# Cases
GET    /api/cases/                           list cases for this tenant
POST   /api/cases/                           create a case
GET    /api/cases/{id}/workflow_status/      current step + available transitions
POST   /api/cases/{id}/attach_workflow/      body: {workflow_template_id}
POST   /api/cases/{id}/advance_step/         body: {transition_id}

# Workflow
GET    /api/workflow-templates/              list templates for this tenant
GET    /api/steps/                           list steps
GET    /api/transitions/                     list transitions

# Law Firms
GET    /api/clients/
GET    /api/attorneys/
GET    /api/documents/
```

---

## PART 5 — Making Changes Safely

### Workflow for every change

```bash
# 1. Create a branch
git checkout -b feature/your-feature-name

# 2. Make your changes and test locally
python manage.py test

# 3. If you changed models, create a migration
python manage.py makemigrations
python manage.py migrate

# 4. Commit
git add .
git commit -m "feat: your change description"

# 5. Open a Pull Request → tests run automatically
# 6. Merge to main → deploys automatically
```

### Emergency: Roll Back a Deploy

```bash
# See recent deploys
fly releases --app suits

# Roll back to the previous version
fly deploy --image <image-id-from-previous-release>
```

### Check Production Logs

```bash
fly logs --app suits          # live logs
fly logs --app suits -n 100   # last 100 lines
```

### Run Django Commands in Production

```bash
fly ssh console --app suits
python manage.py shell
python manage.py createsuperuser
python manage.py migrate
```

---

## Summary Checklist

- [ ] `pip install python-decouple whitenoise dj-database-url`
- [ ] Update `config/settings.py` with env-based config
- [ ] Create `suits/.env` for local dev
- [ ] Update `Dockerfile` (collectstatic fix)
- [ ] Update `fly.toml` (health check + statics path)
- [ ] `fly postgres create` + `fly postgres attach`
- [ ] `fly secrets set` (SECRET_KEY, DEBUG, ALLOWED_HOSTS, CORS, R2 keys)
- [ ] `fly deploy` (first manual deploy)
- [ ] `fly ssh console` → `createsuperuser`
- [ ] Add `FLY_API_TOKEN` to GitHub repo secrets
- [ ] Create `.github/workflows/deploy.yml`
- [ ] Push to main → confirm CI/CD runs
- [ ] Update `CORS_ALLOWED_ORIGINS` when React app is deployed