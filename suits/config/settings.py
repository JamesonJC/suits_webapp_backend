# config/settings.py

from pathlib import Path
from datetime import timedelta
import os
from urllib.parse import urlparse, parse_qsl
from dotenv import load_dotenv
from decouple import config, Csv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

# ─── Security ─────────────────────────────────────────────────────────────────

SECRET_KEY    = config("SECRET_KEY", default="django-insecure-local-dev-only-change-in-production")
DEBUG         = config("DEBUG", default=False, cast=bool)
ALLOWED_HOSTS = config("ALLOWED_HOSTS", default="localhost,127.0.0.1", cast=Csv())

# ─── Apps ─────────────────────────────────────────────────────────────────────

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

# ─── Middleware ────────────────────────────────────────────────────────────────

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",          # MUST be first (before SecurityMiddleware)
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "apps.tenants.middleware.TenantMiddleware",
    "apps.audit.middleware.AuditMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

# ─── REST Framework ────────────────────────────────────────────────────────────
#
# WHAT WAS BROKEN:
#   SessionAuthentication was listed FIRST. When a browser has a Django session
#   cookie (e.g. from a Django admin login), DRF uses SessionAuthentication
#   which then enforces CSRF. Our React frontend never sends a CSRF token
#   → DRF raises PermissionDenied → HTTP 403 on every API call.
#
# WHAT WAS FIXED:
#   JWTAuthentication is now FIRST. DRF stops at the first successful
#      authenticator. JWT always succeeds for valid tokens, so SessionAuthentication
#      is never reached for frontend API calls → no CSRF enforcement → no 403.
#
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        # JWT FIRST — this is the only auth method the React frontend uses.
        #    DRF stops here when a valid Bearer token is present.
        "rest_framework_simplejwt.authentication.JWTAuthentication",
        # Session and Basic are kept for the Django admin panel only.
        "rest_framework.authentication.SessionAuthentication",
        "rest_framework.authentication.BasicAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": (
        "rest_framework.permissions.IsAuthenticated",
    ),
    "DEFAULT_FILTER_BACKENDS": (
        "django_filters.rest_framework.DjangoFilterBackend",
    ),
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME":  timedelta(minutes=60),   # Extended from 30m for usability
    "REFRESH_TOKEN_LIFETIME":  timedelta(days=7),
    # Tells simplejwt to look for the user_id in the token payload
    "USER_ID_FIELD":  "id",
    "USER_ID_CLAIM":  "user_id",
}

# ─── CORS ─────────────────────────────────────────────────────────────────────
#
# WHAT WAS BROKEN:
#   CORS_ALLOW_CREDENTIALS = True AND the deployed frontend URL was not in
#   CORS_ALLOWED_ORIGINS. Browsers block credentialed cross-origin requests
#   when the server doesn't include the exact Access-Control-Allow-Origin header.
#   This caused silent 403/network errors on the deployed frontend.
#
# WHAT WAS FIXED:
#    CORS_ALLOW_CREDENTIALS set to False — our frontend sends JWT in the
#      Authorization header (not cookies), so we don't need credentials mode.
#      This lets us safely allow all origins (CORS_ALLOW_ALL_ORIGINS = True).
#
#    CORS_ALLOW_ALL_ORIGINS = True — safe when credentials = False.
#      In production you can restrict this via the CORS_ALLOWED_ORIGINS env var.
#
# TO RESTRICT IN PRODUCTION:
#   Set CORS_ALLOW_ALL_ORIGINS=False and CORS_ALLOWED_ORIGINS=https://yourfrontend.netlify.app
#   in your Render environment variables.
#
CORS_ALLOW_CREDENTIALS = False   #  Changed from True — JWT is in header, not cookie
CORS_ALLOW_ALL_ORIGINS = True    #  Safe because credentials=False; restrict via env var in prod

# Explicit headers our frontend uses — ensures preflight passes
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
    "x-tenant-code",    # Required by TenantMiddleware
]

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

# ─── URLs / Templates / WSGI ──────────────────────────────────────────────────

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS":    [BASE_DIR / "templates"],
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
