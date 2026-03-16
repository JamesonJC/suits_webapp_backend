# config/settings.py
#
# ENVIRONMENT STRATEGY:
# ─────────────────────
# We use python-decouple to read config from:
#   - A `.env` file when running locally
#   - Environment variables when running on Render
#
# This means the SAME settings.py works in both places.
# You never hardcode secrets — they always come from the environment.

from pathlib import Path
from datetime import timedelta
import os
from decouple import config, Csv

BASE_DIR = Path(__file__).resolve().parent.parent

# ─── Security ────────────────────────────────────────────────────────────────

# SECRET_KEY: Render injects this as an env var.
# Locally it comes from your .env file.
# NEVER hardcode a real secret key in this file.
SECRET_KEY = config("SECRET_KEY", default="django-insecure-local-dev-only-change-in-production")

# DEBUG: Always False on Render. True locally.
DEBUG = config("DEBUG", default=False, cast=bool)

# ALLOWED_HOSTS: The domains Django will accept requests from.
# On Render this will be your .onrender.com domain.
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
# ORDER MATTERS — do not rearrange these.
# WhiteNoise must be second (right after SecurityMiddleware).
# CorsMiddleware must be before CommonMiddleware.

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",      # serves static files in production
    "django.contrib.sessions.middleware.SessionMiddleware",
    "corsheaders.middleware.CorsMiddleware",           # must be before CommonMiddleware
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

# ─── CORS ─────────────────────────────────────────────────────────────────────
# Controls which frontend domains can call this API from a browser.
# Your React app's deployed URL goes here.
# Multiple origins: "https://app.com,https://www.app.com"

CORS_ALLOWED_ORIGINS = config(
    "CORS_ALLOWED_ORIGINS",
    default="http://localhost:3000,http://localhost:5173",
    cast=Csv()
)

# Allow the React frontend to send these headers with every request
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
    "x-tenant-code",    # ← your custom multi-tenant header
]

# ─── Database ─────────────────────────────────────────────────────────────────
# DATABASE_URL is automatically set by Render when you attach a Postgres database.
# Format: postgresql://user:password@host:port/dbname
#
# Locally: if DATABASE_URL is not set, falls back to SQLite.
# This means zero config for local development.

DATABASE_URL = config("DATABASE_URL", default=None)

if DATABASE_URL:
    # Production (Render): parse the connection string automatically
    import dj_database_url
    DATABASES = {
        "default": dj_database_url.parse(
            DATABASE_URL,
            conn_max_age=600,        # keep connections alive for 10 minutes (performance)
            ssl_require=True,        # Render Postgres requires SSL
        )
    }
else:
    # Local development: SQLite — no setup needed
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }

# ─── Cloudflare R2 (File Storage) ────────────────────────────────────────────
# These are read from env vars — never hardcoded.
# Set them in Render dashboard → Environment → Environment Variables.

CLOUDFLARE_R2_KEY_ID     = config("CLOUDFLARE_R2_KEY_ID",     default="")
CLOUDFLARE_R2_SECRET_KEY = config("CLOUDFLARE_R2_SECRET_KEY", default="")
CLOUDFLARE_R2_BUCKET     = config("CLOUDFLARE_R2_BUCKET",     default="")
CLOUDFLARE_R2_ACCOUNT_ID = config("CLOUDFLARE_R2_ACCOUNT_ID", default="")

# ─── Static Files ─────────────────────────────────────────────────────────────
# WhiteNoise serves Django's static files (admin CSS etc.) directly.
# No separate file server needed — Gunicorn handles it all.
# CompressedManifestStaticFilesStorage adds cache-busting hashes to filenames.

STATIC_URL  = "/static/"
STATIC_ROOT = os.path.join(BASE_DIR, "staticfiles")
STATICFILES_DIRS = (
    [os.path.join(BASE_DIR, "static")] 
    if os.path.exists(os.path.join(BASE_DIR, "static")) 
    else []
)
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

# ─── URLs / Templates / WSGI ─────────────────────────────────────────────────

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

# ─── Auth ─────────────────────────────────────────────────────────────────────

AUTH_USER_MODEL = "users.User"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# ─── Internationalisation ─────────────────────────────────────────────────────

LANGUAGE_CODE = "en-us"
TIME_ZONE     = "UTC"
USE_I18N      = True
USE_TZ        = True

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"