# config/settings.py

from pathlib import Path
from datetime import timedelta
import os
from urllib.parse import urlparse, parse_qsl
from dotenv import load_dotenv
from decouple import config, Csv

# Load .env file for local development
# On Render, environment variables are injected directly — load_dotenv() is harmless there
load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

# ─── Security ────────────────────────────────────────────────────────────────

SECRET_KEY = config("SECRET_KEY", default="django-insecure-local-dev-only-change-in-production")
DEBUG = config("DEBUG", default=False, cast=bool)
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
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "corsheaders.middleware.CorsMiddleware",  # must be before CommonMiddleware
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

# Allow your frontend (Codespaces) + local dev
CORS_ALLOWED_ORIGINS = config(
    "CORS_ALLOWED_ORIGINS",
    default="http://localhost:3000,http://localhost:5173,https://animated-enigma-w9w7qq4599jh9qvw-3000.app.github.dev",
    cast=Csv()
)

# Allow cookies / auth headers if needed
CORS_ALLOW_CREDENTIALS = True

# Explicit headers (safe + includes JWT)
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
    "x-tenant-code",
]

# OPTIONAL: during debugging only (uncomment if still stuck)
# CORS_ALLOW_ALL_ORIGINS = True

# ─── Database ─────────────────────────────────────────────────────────────────

DATABASE_URL = os.getenv("DATABASE_URL")

if DATABASE_URL:
    tmpPostgres = urlparse(DATABASE_URL)
    DATABASES = {
        "default": {
            "ENGINE":   "django.db.backends.postgresql",
            "NAME":     tmpPostgres.path.replace("/", ""),
            "USER":     tmpPostgres.username,
            "PASSWORD": tmpPostgres.password,
            "HOST":     tmpPostgres.hostname,
            "PORT":     tmpPostgres.port or 5432,
            "OPTIONS":  dict(parse_qsl(tmpPostgres.query)),
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME":   BASE_DIR / "db.sqlite3",
        }
    }

# ─── Cloudflare R2 ────────────────────────────────────────────────────────────

CLOUDFLARE_R2_KEY_ID     = config("CLOUDFLARE_R2_KEY_ID",     default="")
CLOUDFLARE_R2_SECRET_KEY = config("CLOUDFLARE_R2_SECRET_KEY", default="")
CLOUDFLARE_R2_BUCKET     = config("CLOUDFLARE_R2_BUCKET",     default="")
CLOUDFLARE_R2_ACCOUNT_ID = config("CLOUDFLARE_R2_ACCOUNT_ID", default="")

# ─── Static Files ─────────────────────────────────────────────────────────────

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

LANGUAGE_CODE      = "en-us"
TIME_ZONE          = "UTC"
USE_I18N           = True
USE_TZ             = True
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
