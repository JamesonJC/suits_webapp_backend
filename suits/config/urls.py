# suits/config/urls.py
#
# Master URL configuration — all routes registered here.
#
# ─────────────────────────────────────────────────────────────────────────────
# WHAT WAS FIXED:
#
#   PROBLEM — LawFirmViewSet registered TWICE:
#     The config-level router registered LawFirmViewSet on r"lawfirms".
#     lawfirms/urls.py ALSO registered it on r"lawfirms" with the same basename.
#     When Django included both, it created duplicate URL patterns.
#     Django uses the FIRST match so technically only one served requests,
#     but the redundancy was confusing, caused warnings, and made routes fragile.
#
#     Fix: removed LawFirmViewSet from the config-level router entirely.
#     It is already correctly registered inside apps/lawfirms/urls.py along with
#     attorneys, clients, cases, and documents — all included via:
#       path("api/", include("apps.lawfirms.urls"))
#
#   URL STRUCTURE (clean, no duplicates):
#     POST /api/auth/login/              → LoginView (our custom view)
#     POST /api/auth/refresh/            → TokenRefreshView (simplejwt)
#     GET  /api/auth/me/                 → MeView (via apps.users.urls)
#     /admin/                            → Django admin
#     /api/tenants/                      → TenantViewSet  (admin only)
#     /api/lawfirms/                     → LawFirmViewSet  ← from lawfirms.urls
#     /api/attorneys/                    → AttorneyViewSet ← from lawfirms.urls
#     /api/clients/                      → ClientViewSet  ← from lawfirms.urls
#     /api/cases/                        → CaseViewSet    ← from lawfirms.urls
#     /api/cases/{id}/attach_workflow/   → CaseViewSet.attach_workflow
#     /api/cases/{id}/advance_step/      → CaseViewSet.advance_step
#     /api/cases/{id}/workflow_status/   → CaseViewSet.workflow_status
#     /api/documents/                    → DocumentViewSet ← from lawfirms.urls
#     /api/workflow-templates/           → WorkflowTemplateViewSet ← workflows.urls
#     /api/steps/                        → WorkflowStepViewSet
#     /api/transitions/                  → WorkflowTransitionViewSet
# ─────────────────────────────────────────────────────────────────────────────

from django.contrib             import admin
from django.urls                import path, include
from rest_framework.routers     import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView

from apps.users.views   import LoginView
from apps.tenants.views import TenantViewSet

# ── Config-level router — only what is NOT already in an app's own urls.py ───
#    FIX: LawFirmViewSet REMOVED from here — it lives in apps/lawfirms/urls.py.
#    Keeping it here caused duplicate /api/lawfirms/ registrations.
router = DefaultRouter()
router.register(r'tenants', TenantViewSet, basename='tenant')

urlpatterns = [

    # ── Authentication ──────────────────────────────────────────────────────
    # Our custom LoginView — accepts "login" field (email OR username),
    # returns {access, refresh, user: {is_staff, tenant_code, ...}}
    path('api/auth/login/',   LoginView.as_view(),        name='login'),
    # simplejwt refresh — accepts {refresh}, returns {access}
    path('api/auth/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    # MeView — GET current user profile (registered in users/urls.py)
    path('api/auth/',         include('apps.users.urls')),

    # ── Django admin panel ──────────────────────────────────────────────────
    path('admin/', admin.site.urls),

    # ── Config-level router (tenants only) ──────────────────────────────────
    path('api/', include(router.urls)),

    # ── App-level routers (included from each app's urls.py) ────────────────
    # All law firm data: /api/lawfirms/, /api/attorneys/, /api/clients/,
    #                    /api/cases/, /api/documents/
    path('api/', include('apps.lawfirms.urls')),

    # All workflow data: /api/workflow-templates/, /api/steps/, /api/transitions/
    path('api/', include('apps.workflows.urls')),
    path('api/', include('apps.jobs.urls')),
]