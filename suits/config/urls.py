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

from django.contrib import admin
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from apps.tenants.views import TenantViewSet
from apps.lawfirms.views import LawFirmViewSet

# ── Main API Router ─────────────────────────────────────────────────────────
# ViewSets registered here get full CRUD automatically
router = DefaultRouter()
router.register(r"tenants",  TenantViewSet,  basename="tenant")
router.register(r"lawfirms", LawFirmViewSet, basename="lawfirm")

urlpatterns = [
    # ── Authentication ──────────────────────────────────────────────────────
    # simplejwt provides login (token obtain) and token refresh
    path("api/auth/login/",   TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("api/auth/refresh/", TokenRefreshView.as_view(),    name="token_refresh"),

    # NEW: User profile endpoint — frontend calls this after login
    # to get tenant_code for the X-Tenant-Code header
    path("api/auth/", include("apps.users.urls")),

    # ── Admin Panel ─────────────────────────────────────────────────────────
    path("admin/", admin.site.urls),

    # ── API Routers ─────────────────────────────────────────────────────────
    path("api/", include(router.urls)),           # /api/tenants/, /api/lawfirms/
    path("api/", include("apps.workflows.urls")), # /api/workflow-templates/, /api/steps/, /api/transitions/
    path("api/", include("apps.lawfirms.urls")),  # /api/attorneys/, /api/clients/, /api/cases/, /api/documents/
]