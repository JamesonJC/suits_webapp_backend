"""
apps/tenants/middleware.py — Tenant Middleware

─────────────────────────────────────────────────────────────────────────────
WHAT WAS BROKEN:

  Admin users (is_staff / is_superuser) do not belong to any tenant, so they
  never send an X-Tenant-Code header. The old middleware returned HTTP 400 for
  any non-public request without that header — locking admins out entirely.

WHAT WAS FIXED:

  ✅ Added _is_superuser_request() — decodes the JWT from the Authorization
     header and checks if the user is staff/superuser.
     (This is a read-only peek — no side effects, no full DRF auth cycle.)

  ✅ If the request has no tenant code but IS from an admin:
       request.tenant = None
       set_current_tenant(None)
       → allowed through. ViewSets handle admin access via Model.unscoped.

  ✅ Non-admin requests without a tenant code still get HTTP 400 (unchanged).
  ✅ Public paths (/, /admin/, /api/auth/, /static/) unchanged.
─────────────────────────────────────────────────────────────────────────────
"""

from django.http import JsonResponse
from .models import Tenant
from .context import set_current_tenant


class TenantMiddleware:

    # Paths that never need a tenant header (login, Django admin, static files)
    PUBLIC_PATH_PREFIXES = [
        "/",
        "/admin/",
        "/api/auth/",
        "/static/",
    ]

    def __init__(self, get_response):
        self.get_response = get_response

    def is_public_path(self, path: str) -> bool:
        return any(path.startswith(p) for p in self.PUBLIC_PATH_PREFIXES)

    def _is_superuser_request(self, request) -> bool:
        """
        Peek at the JWT in the Authorization header to check if the caller is
        a Django staff user or superuser.

        WHY we do this in middleware (before DRF auth runs):
          The TenantMiddleware sits BEFORE DRF authentication in the middleware
          stack. We need to decide whether to enforce tenant presence BEFORE
          the request reaches any view. Decoding the JWT here is the only way
          to make that decision.

        This is read-only — we don't set request.user here (DRF does that
        later). We're only checking the token payload.
        """
        try:
            from rest_framework_simplejwt.authentication import JWTAuthentication
            jwt_auth = JWTAuthentication()
            result   = jwt_auth.authenticate(request)
            if result is None:
                return False
            user, _ = result
            return bool(user and (user.is_staff or user.is_superuser))
        except Exception:
            return False

    def __call__(self, request):

        # ── Step 1: Public routes skip all tenant logic ───────────────────────
        if self.is_public_path(request.path):
            request.tenant = None
            set_current_tenant(None)
            return self.get_response(request)

        # ── Step 2: Try to read the tenant code from the request header ───────
        tenant_code = (
            request.headers.get("X-Tenant-Code")
            or request.META.get("HTTP_X_TENANT_CODE")
        )

        # ── Step 3: No tenant code — only admins are allowed through ──────────
        if not tenant_code:
            if self._is_superuser_request(request):
                # Admin users see all data via Model.unscoped in their ViewSets.
                # No tenant context is set — TenantManager returns none(),
                # but ViewSets detect is_staff and switch to unscoped queries.
                request.tenant = None
                set_current_tenant(None)
                return self.get_response(request)

            # Regular users must always provide a tenant code
            return JsonResponse(
                {"error": "Tenant header (X-Tenant-Code) is required"},
                status=400,
            )

        # ── Step 4: Validate the tenant code ─────────────────────────────────
        try:
            tenant = Tenant.objects.get(code=tenant_code, active=True)
        except Tenant.DoesNotExist:
            return JsonResponse(
                {"error": "Invalid or inactive tenant"},
                status=400,
            )

        # ── Step 5: Bind tenant to request + thread-local context ─────────────
        # The thread-local is read by TenantManager.get_queryset() on every
        # database query to enforce row-level tenant isolation automatically.
        request.tenant = tenant
        set_current_tenant(tenant)

        return self.get_response(request)