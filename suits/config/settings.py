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