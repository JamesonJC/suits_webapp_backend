# config/urls.py

from django.contrib import admin
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from apps.tenants.views import TenantViewSet
from apps.lawfirms.views import LawFirmViewSet

# ✅ FIX: The original registered WorkflowTemplateViewSet and WorkflowStepViewSet
#         BOTH in this router AND inside apps/workflows/urls.py (via include).
#         That produced duplicate conflicting URL patterns.
#
#         Rule: each ViewSet is registered in exactly ONE place.
#         - Workflows → apps/workflows/urls.py (included below)
#         - Lawfirms  → apps/lawfirms/urls.py  (included below)
#         - Tenants, LawFirms top-level → registered here in the main router

router = DefaultRouter()
router.register(r"tenants",  TenantViewSet,  basename="tenant")
router.register(r"lawfirms", LawFirmViewSet, basename="lawfirm")

urlpatterns = [
    # ── Auth ──────────────────────────────────────────────────────────────────
    path("api/auth/login/",   TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("api/auth/refresh/", TokenRefreshView.as_view(),    name="token_refresh"),

    # ── Admin ─────────────────────────────────────────────────────────────────
    path("admin/", admin.site.urls),

    # ── API routers ───────────────────────────────────────────────────────────
    path("api/", include(router.urls)),              # /api/tenants/, /api/lawfirms/
    path("api/", include("apps.workflows.urls")),    # /api/workflow-templates/, /api/steps/, /api/transitions/
    path("api/", include("apps.lawfirms.urls")),     # /api/clients/, /api/cases/, /api/documents/
]