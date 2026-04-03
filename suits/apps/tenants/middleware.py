# apps/tenants/middleware.py

from django.http import JsonResponse
from .models import Tenant
from .context import set_current_tenant


class TenantMiddleware:
    """
    Resolves tenant from X-Tenant-Code header.

    TEMP CHANGE:
    - Tenant requirement is DISABLED for now
    - Middleware will NOT block requests if tenant is missing

    TODO (later):
    - Re-enable tenant enforcement for protected endpoints
    """

    PUBLIC_PATH_PREFIXES = [
        "",
        "/",                     # root
        "/admin/",
        "/api/auth/",            # login + refresh
        "/static/",
    ]

    def __init__(self, get_response):
        self.get_response = get_response

    def is_public_path(self, path: str) -> bool:
        return any(path.startswith(p) for p in self.PUBLIC_PATH_PREFIXES)

    def __call__(self, request):
        request.tenant = None
        set_current_tenant(None)

        path = request.path

        # 1. Allow public routes WITHOUT tenant
        if self.is_public_path(path):
            return self.get_response(request)

        # 2. TEMP: Disable tenant requirement completely
        tenant_code = (
            request.headers.get("X-Tenant-Code")
            or request.META.get("HTTP_X_TENANT_CODE")
        )

        # ─────────────────────────────────────────────
        # 🚨 TEMP DISABLE (commented out enforcement)
        # ─────────────────────────────────────────────
        #
        # if not tenant_code:
        #     return JsonResponse(
        #         {"error": "Tenant header (X-Tenant-Code) is required"},
        #         status=400
        #     )
        #
        # try:
        #     tenant = Tenant.objects.get(code=tenant_code, active=True)
        # except Tenant.DoesNotExist:
        #     return JsonResponse(
        #         {"error": "Invalid or inactive tenant"},
        #         status=400
        #     )
        #
        # request.tenant = tenant
        # set_current_tenant(tenant)
        #
        # ─────────────────────────────────────────────

        # ✅ Instead: only set tenant IF provided (non-blocking)
        if tenant_code:
            try:
                tenant = Tenant.objects.get(code=tenant_code, active=True)
                request.tenant = tenant
                set_current_tenant(tenant)
            except Tenant.DoesNotExist:
                # TEMP: ignore invalid tenant instead of blocking
                pass

        return self.get_response(request)
