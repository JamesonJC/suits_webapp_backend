# suits/config/urls.py
#
# The master URL configuration for the entire Django project.
# All API endpoints are registered here (either directly or via include()).
#
# URL structure:
#   /api/auth/login/        → JWT token obtain (simplejwt)
#   /api/auth/refresh/      → JWT token refresh (simplejwt)
#   /api/auth/me/           → NEW: current user profile + tenant code
#   /admin/                 → Django admin panel
#   /api/tenants/           → Tenant CRUD (admin only)
#   /api/lawfirms/          → Law firm CRUD
#   /api/workflow-templates/ → Workflow template CRUD
#   /api/steps/             → Workflow step CRUD
#   /api/transitions/       → Workflow transition CRUD
#   /api/attorneys/         → Attorney CRUD
#   /api/clients/           → Client CRUD
#   /api/cases/             → Case CRUD + workflow actions
#   /api/documents/         → Document CRUD


#
# ─────────────────────────────────────────────────────────────────────────────
# WHAT WAS BROKEN AND WHY:
#
#   PREVIOUS CODE:
#     path("api/auth/login/", TokenObtainPairView.as_view(), ...)
#
#   TokenObtainPairView (simplejwt's built-in) expects the field "username",
#   but our authService.js sends the field "login". So login always returned
#   400 {"username": ["This field is required."]}
#
#   Even if tokens were obtained another way, TokenObtainPairView returns ONLY
#   {access, refresh} — no user object. authService.js then throws
#   "User data not returned from login." and never stores tenant_code,
#   is_staff, or is_superuser. This caused every downstream API call to
#   have no X-Tenant-Code header and no way to skip tenant checks for admins.
#
# WHAT WAS FIXED:
#    /api/auth/login/ now routes to our custom LoginView which:
#       - Accepts "login" field (email OR username)
#       - Returns {access, refresh, user: {is_staff, is_superuser, tenant_code, ...}}
#    /api/auth/refresh/ still uses simplejwt's TokenRefreshView (unchanged)
#    /api/auth/me/ is registered via include("apps.users.urls") (unchanged)
#    All other routes are unchanged
# ─────────────────────────────────────────────────────────────────────────────

from django.contrib import admin
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView  # refresh only — login is custom

# ← CHANGED: import our own LoginView instead of TokenObtainPairView
from apps.users.views import LoginView
from apps.tenants.views import TenantViewSet
from apps.lawfirms.views import LawFirmViewSet

# ── Main API Router ──────────────────────────────────────────────────────────
router = DefaultRouter()
router.register(r"tenants",  TenantViewSet,  basename="tenant")
router.register(r"lawfirms", LawFirmViewSet, basename="lawfirm")

urlpatterns = [

    # ── Auth ────────────────────────────────────────────────────────────────
    #  CHANGED: LoginView (our custom view) replaces TokenObtainPairView.
    #   - Accepts: POST { login: "email_or_username", password: "..." }
    #   - Returns: { access, refresh, user: { id, email, is_staff, tenant_code, ... } }
    path("api/auth/login/",   LoginView.as_view(),      name="login"),

    # Token refresh is still handled by simplejwt (unchanged behaviour)
    path("api/auth/refresh/", TokenRefreshView.as_view(), name="token_refresh"),

    # /api/auth/me/ — returns full user profile (registered in apps/users/urls.py)
    path("api/auth/", include("apps.users.urls")),

    # ── Django admin panel ──────────────────────────────────────────────────
    path("admin/", admin.site.urls),

    # ── Data API routes ─────────────────────────────────────────────────────
    path("api/", include(router.urls)),            # /api/tenants/, /api/lawfirms/
    path("api/", include("apps.workflows.urls")),  # /api/workflow-templates/, /api/steps/, /api/transitions/
    path("api/", include("apps.lawfirms.urls")),   # /api/attorneys/, /api/clients/, /api/cases/, /api/documents/
]
