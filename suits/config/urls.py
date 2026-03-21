# config/urls.py

from django.contrib import admin
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from apps.tenants.views import TenantViewSet
from apps.lawfirms.views import LawFirmViewSet
from apps.core.views import api_root
# Our view accepts email OR username and returns specific error messages
from apps.users.views import LoginView

# FIX: The original registered WorkflowTemplateViewSet and WorkflowStepViewSet
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
    # Custom login — accepts email or username, returns specific errors
    path("api/auth/login/",   LoginView.as_view(),       name="token_obtain_pair"),
    # Standard refresh — unchanged
    path("api/auth/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
 
    # ── Admin ─────────────────────────────────────────────────────────────────
    path("admin/", admin.site.urls),
 
    # ── API routers ───────────────────────────────────────────────────────────
    path("api/", include(router.urls)),
    path("api/", include("apps.workflows.urls")),
    path("api/", include("apps.lawfirms.urls")),
]
