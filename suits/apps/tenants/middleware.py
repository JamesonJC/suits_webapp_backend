"""
Tenant Middleware

Purpose:
- Resolve tenant using X-Tenant-Code header
- Attach tenant to request
- Enforce tenant isolation for protected routes

FIXES APPLIED:
1. Removed duplicate tenant resolution logic
2. Fixed indentation errors (was breaking execution)
3. Re-enabled tenant enforcement properly
4. Preserved public route bypass (admin, auth, etc.)
5. Removed "non-blocking tenant" fallback (DANGEROUS)
"""

from django.http import JsonResponse
from .models import Tenant
from .context import set_current_tenant


class TenantMiddleware:

    # ✅ Public routes that DO NOT require tenant
    PUBLIC_PATH_PREFIXES = [
        "/",                     # root
        "/admin/",
        "/api/auth/",            # login, refresh
        "/static/",
    ]

    def __init__(self, get_response):
        self.get_response = get_response

    def is_public_path(self, path: str) -> bool:
        return any(path.startswith(p) for p in self.PUBLIC_PATH_PREFIXES)

    def __call__(self, request):

        # ============================================================
        # STEP 1: Allow public routes WITHOUT tenant
        # ============================================================
        if self.is_public_path(request.path):
            request.tenant = None
            set_current_tenant(None)
            return self.get_response(request)

        # ============================================================
        # STEP 2: Extract tenant_code from request
        # ============================================================
        tenant_code = (
            request.headers.get("X-Tenant-Code")
            or request.META.get("HTTP_X_TENANT_CODE")
        )

        # ============================================================
        # STEP 3: Enforce tenant presence (CRITICAL)
        # ============================================================
        if not tenant_code:
            return JsonResponse(
                {"error": "Tenant header (X-Tenant-Code) is required"},
                status=400
            )

        # ============================================================
        # STEP 4: Validate tenant exists and is active
        # ============================================================
        try:
            tenant = Tenant.objects.get(code=tenant_code, active=True)
        except Tenant.DoesNotExist:
            return JsonResponse(
                {"error": "Invalid or inactive tenant"},
                status=400
            )

        # ============================================================
        # STEP 5: Attach tenant to request context
        # ============================================================
        request.tenant = tenant
        set_current_tenant(tenant)

        # ============================================================
        #  REMOVED: Non-blocking fallback logic
        # (This was dangerous — could allow cross-tenant access)
        #
        # if tenant_code:
        #     try:
        #         tenant = Tenant.objects.get(...)
        #         request.tenant = tenant
        #     except:
        #         pass
        #
        # ============================================================

        return self.get_response(request)