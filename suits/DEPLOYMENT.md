# Suits Backend — Render Deployment Guide

> Deploy the Django backend to Render.com with PostgreSQL,
> GitHub Actions CI/CD, and React frontend readiness.
>
> **Stack:** Django 6.0.2 · Gunicorn · WhiteNoise · PostgreSQL · Render

---

## What Render Does For You (vs OCI)

```
Render handles automatically:          You handled manually on OCI:
✅ SSL certificate (HTTPS)              nginx + certbot
✅ Deploy on git push                   GitHub Actions SSH
✅ Managed Postgres                     apt install postgresql
✅ Zero-downtime deploys                systemd + careful restart
✅ Logs in dashboard                    journalctl
✅ Custom domains                       DNS config
```

Render is simpler but less flexible. Perfect for getting your API
live fast so you can focus on building the React frontend.

---

## Architecture on Render

```
GitHub (push to main)
        ↓
Render detects the push
        ↓
build.sh runs:
  - pip install -r requirements.txt
  - python manage.py migrate
  - python manage.py collectstatic
        ↓
Gunicorn starts (Render manages this)
        ↓
Your API is live at https://suits-backend.onrender.com
        ↓
React frontend calls the API using that URL
```

---

## PART 1 — File Changes (Do These First Locally)

### Files to update in your repo:

| File | What changed |
|------|-------------|
| `suits/config/settings.py` | Full rewrite — env-based config |
| `suits/requirements.txt` | Added gunicorn, whitenoise, dj-database-url, python-decouple |
| `suits/build.sh` | New file — Render runs this on every deploy |
| `suits/.env.example` | New file — template for local dev (commit this, not .env) |

### Step 1.1 — Apply the file changes

Replace these files with the ones provided:
- `suits/config/settings.py`
- `suits/requirements.txt`
- Create `suits/build.sh`
- Create `suits/.env.example`

### Step 1.2 — Create your local .env (do NOT commit this)

```bash
cd suits
cp .env.example .env
# Edit .env and fill in your values
```

Make sure `.env` is in your `.gitignore` — it already is in your project.

### Step 1.3 — Make build.sh executable

```bash
chmod +x suits/build.sh
```

### Step 1.4 — Test locally before pushing

```bash
cd suits
pip install -r requirements.txt
python manage.py check
python manage.py runserver
```

### Step 1.5 — Commit and push

```bash
git add suits/config/settings.py suits/requirements.txt suits/build.sh suits/.env.example
git commit -m "feat(deploy): add Render deployment config — settings, build script, requirements"
git push origin main
```

---

## PART 2 — Set Up Render

### Step 2.1 — Create a Render Account

Go to https://render.com and sign up with your GitHub account.
This lets Render access your repos directly.

### Step 2.2 — Create a PostgreSQL Database

Render's free Postgres tier is perfect for getting started.

1. In the Render dashboard click **New → PostgreSQL**
2. Fill in:
   ```
   Name:    suits-db
   Region:  Frankfurt (EU) or Singapore — closest to your users
   Plan:    Free
   ```
3. Click **Create Database**
4. Wait for it to spin up (about 1 minute)
5. On the database page, find **Internal Database URL** — copy it.
   It looks like:
   ```
   postgresql://suits_db_user:xxxxx@dpg-xxxxx/suits_db
   ```
   Keep this — you'll paste it into the web service next.

> **Important:** Render's free Postgres databases are deleted after
> 90 days of inactivity. Upgrade to paid ($7/month) for production use.

### Step 2.3 — Create the Web Service

1. Click **New → Web Service**
2. Connect your GitHub repo (`suits_webapp_backend`)
3. Fill in the settings:

```
Name:               suits-backend
Region:             Same as your database
Branch:             main
Root Directory:     suits          ← important! your Django app is in /suits
Runtime:            Python 3
Build Command:      chmod +x build.sh && ./build.sh
Start Command:      gunicorn config.wsgi:application --bind 0.0.0.0:$PORT --workers 2
Plan:               Free (or Starter for always-on)
```

> **Note on free plan:** Render's free web service spins down after
> 15 minutes of inactivity and takes ~30 seconds to wake up on the
> next request. For a backend that React calls, upgrade to Starter
> ($7/month) for always-on. Your choice.

4. Click **Create Web Service** — but don't let it build yet.
   We need to add environment variables first.

### Step 2.4 — Add Environment Variables

On your web service page, go to **Environment → Environment Variables**.
Add these one by one:

| Key | Value |
|-----|-------|
| `SECRET_KEY` | Generate one (see below) |
| `DEBUG` | `False` |
| `ALLOWED_HOSTS` | `suits-backend.onrender.com` |
| `DATABASE_URL` | Paste the Internal Database URL from Step 2.2 |
| `CORS_ALLOWED_ORIGINS` | `http://localhost:3000` (update when React is deployed) |
| `CLOUDFLARE_R2_KEY_ID` | Your R2 key |
| `CLOUDFLARE_R2_SECRET_KEY` | Your R2 secret |
| `CLOUDFLARE_R2_BUCKET` | Your bucket name |
| `CLOUDFLARE_R2_ACCOUNT_ID` | Your account ID |

**Generate a SECRET_KEY:**
```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

### Step 2.5 — Trigger First Deploy

Click **Manual Deploy → Deploy latest commit**.

Watch the logs — you'll see:
```
▶ Installing dependencies...
▶ Running migrations...
  Applying tenants.0001_initial... OK
  ...
▶ Collecting static files...
✅ Build complete.
==> Starting service with gunicorn...
```

Once you see `Your service is live`, your API is at:
```
https://suits-backend.onrender.com
```

### Step 2.6 — Create Your Superuser

Render has a shell you can access from the dashboard:

1. Go to your web service
2. Click **Shell** tab
3. Run:
```bash
python manage.py createsuperuser
```

Your admin is now at:
```
https://suits-backend.onrender.com/admin/
```

---

## PART 3 — GitHub Actions CI/CD

Render auto-deploys on every push to main already. GitHub Actions adds
automatic **testing** before the deploy goes live — so broken code
never reaches production.

### Step 3.1 — Get a Render Deploy Hook

1. On your Render web service, go to **Settings → Deploy Hook**
2. Copy the URL — it looks like:
   ```
   https://api.render.com/deploy/srv-xxxxx?key=xxxxx
   ```

### Step 3.2 — Add Secret to GitHub

Go to your GitHub repo → **Settings → Secrets and variables → Actions → New repository secret**

| Name | Value |
|------|-------|
| `RENDER_DEPLOY_HOOK` | The URL from step 3.1 |

### Step 3.3 — Create the Workflow File

```bash
mkdir -p .github/workflows
```

Create `.github/workflows/deploy.yml`:

```yaml
# .github/workflows/deploy.yml
#
# On every push to main:
#   1. Run Django tests against a real PostgreSQL database
#   2. If tests pass → trigger Render to deploy
#   3. If tests fail → deploy is blocked

name: Test and Deploy

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  # ─── Run Tests ──────────────────────────────────────────────────────────────
  test:
    name: Run Tests
    runs-on: ubuntu-latest

    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_DB: suits_test
          POSTGRES_USER: suits
          POSTGRES_PASSWORD: suits
        ports: ["5432:5432"]
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5

    env:
      SECRET_KEY: "ci-test-key-not-real"
      DEBUG: "True"
      ALLOWED_HOSTS: "localhost"
      DATABASE_URL: "postgresql://suits:suits@localhost:5432/suits_test"

    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
          cache: "pip"

      - name: Install dependencies
        working-directory: suits
        run: pip install -r requirements.txt

      - name: Run migrations
        working-directory: suits
        run: python manage.py migrate --noinput

      - name: Run tests
        working-directory: suits
        run: python manage.py test --verbosity=2

  # ─── Deploy to Render ───────────────────────────────────────────────────────
  deploy:
    name: Deploy to Render
    runs-on: ubuntu-latest
    needs: test                           # only if tests pass
    if: github.ref == 'refs/heads/main'   # only from main, not PRs

    steps:
      - name: Trigger Render Deploy
        run: |
          curl -X POST "${{ secrets.RENDER_DEPLOY_HOOK }}"
          echo "✅ Deploy triggered on Render"
```

Commit and push this file. From now on:
- Every PR → tests run, no deploy
- Every merge to main → tests run, then Render deploys

---

## PART 4 — React Frontend Connection

### The two headers every React request must send

```javascript
// src/lib/api.js

const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000";
// For Create React App use: process.env.REACT_APP_API_URL

export async function apiRequest(path, options = {}, tenantCode) {
  const token = localStorage.getItem("access_token");

  const response = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      // JWT token — required for all protected endpoints
      "Authorization": token ? `Bearer ${token}` : "",
      // Your multi-tenant header — required for ALL requests
      "X-Tenant-Code": tenantCode,
      ...options.headers,
    },
  });

  return response;
}
```

### Login and store the token

```javascript
async function login(username, password, tenantCode) {
  const res = await fetch(`${API_BASE}/api/auth/login/`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-Tenant-Code": tenantCode,
    },
    body: JSON.stringify({ username, password }),
  });
  const data = await res.json();
  localStorage.setItem("access_token", data.access);
  localStorage.setItem("refresh_token", data.refresh);
}
```

### Set API URL per environment

**.env.local** (local dev):
```
VITE_API_URL=http://localhost:8000
```

**.env.production** (deployed React):
```
VITE_API_URL=https://suits-backend.onrender.com
```

### Update CORS when React is deployed

Once your React app is deployed (Vercel, Netlify etc.), add its URL to Render:

Render Dashboard → suits-backend → **Environment → Environment Variables**
```
CORS_ALLOWED_ORIGINS = https://your-react-app.vercel.app,http://localhost:3000
```

Render auto-redeploys when you save env var changes.

---

## PART 5 — Key API Endpoints Reference

```
# Authentication
POST  /api/auth/login/              {username, password}  → {access, refresh}
POST  /api/auth/refresh/            {refresh}             → {access}

# Cases & Workflow
GET   /api/cases/                   list cases
POST  /api/cases/                   create case
GET   /api/cases/{id}/workflow_status/     current step + available transitions
POST  /api/cases/{id}/attach_workflow/     {workflow_template_id}
POST  /api/cases/{id}/advance_step/        {transition_id}

# Workflow Templates
GET   /api/workflow-templates/      list templates
GET   /api/steps/                   list steps
GET   /api/transitions/             list transitions

# Law Firm
GET   /api/clients/
GET   /api/attorneys/
GET   /api/lawfirms/
GET   /api/documents/
```

---

## Summary Checklist

**Local Changes**
- [ ] Replace `suits/config/settings.py`
- [ ] Replace `suits/requirements.txt`
- [ ] Create `suits/build.sh` and run `chmod +x suits/build.sh`
- [ ] Create `suits/.env.example`
- [ ] Create `suits/.env` (from .env.example, never commit)
- [ ] `pip install -r requirements.txt`
- [ ] `python manage.py check` — confirm no errors
- [ ] Commit and push

**Render Setup**
- [ ] Create Render account (connect GitHub)
- [ ] Create PostgreSQL database (free tier)
- [ ] Create Web Service — Root Directory: `suits`
- [ ] Set all environment variables
- [ ] Manual deploy → confirm build logs succeed
- [ ] `python manage.py createsuperuser` via Render Shell
- [ ] Test: `https://suits-backend.onrender.com/admin/`

**CI/CD**
- [ ] Copy Render Deploy Hook URL
- [ ] Add `RENDER_DEPLOY_HOOK` secret to GitHub
- [ ] Create `.github/workflows/deploy.yml`
- [ ] Push → confirm Actions run green

**React Integration**
- [ ] Set `VITE_API_URL` in React project
- [ ] Update `CORS_ALLOWED_ORIGINS` in Render env vars when React is deployed