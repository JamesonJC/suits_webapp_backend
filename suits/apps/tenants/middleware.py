"""
apps/tenants/middleware.py — Tenant Middleware

─────────────────────────────────────────────────────────────────────────────
WHAT WAS BROKEN:

  1. PUBLIC_PATH_PREFIXES contained "/".
     Because ALL paths start with "/", EVERY request was treated as public.
     The middleware always called set_current_tenant(None), which made the
     TenantManager return qs.none() for every firm-user query → empty data.

  2. Admin users (is_staff/is_superuser) have no tenant, so they never send
     X-Tenant-Code. The middleware would return 400 for them (if the "/" bug
     were fixed). The admin bypass via JWT peeking was correct in concept
     but would never run because "/" caught everything first.

WHAT WAS FIXED:

   Removed "/" from PUBLIC_PATH_PREFIXES. "/" (root) is handled via an
     exact-match check instead. This means all /api/ paths are now properly
     subject to tenant validation.

   PUBLIC_PATH_PREFIXES now only lists prefixes that truly need no tenant:
       /admin/     → Django admin panel (uses session auth, not tenant)
       /api/auth/  → Login, refresh, me — no tenant needed at auth time
       /static/    → Static assets

   Admin bypass (_is_superuser_request) now actually runs for /api/ paths
     that lack an X-Tenant-Code header, correctly passing admins through with
     tenant=None while blocking non-admin requests without a code (400).

   Firm users who send a valid X-Tenant-Code get tenant set correctly,
     so TenantManager filters properly.
─────────────────────────────────────────────────────────────────────────────
"""

from django.http import JsonResponse
from .models import Tenant
from .context import set_current_tenant


class TenantMiddleware:

    #  FIX: "/" removed — it matched every path, bypassing all tenant checks.
    # These are path PREFIXES. "/" would prefix-match /api/cases/, /api/clients/,
    # everything — so it made every request public. Now only genuinely public
    # prefixes are listed here.
    PUBLIC_PATH_PREFIXES = (
        "/admin/",    # Django admin — uses session auth, no tenant header needed
        "/api/auth/", # Login, refresh, me — tenant resolved post-login
        "/static/",   # Static files
        "/favicon",   # Browser favicon requests
    )

    # Exact paths that bypass tenant logic (root only)
    PUBLIC_EXACT_PATHS = ("/",)

    def __init__(self, get_response):
        self.get_response = get_response

    def is_public_path(self, path: str) -> bool:
        """
        Returns True if this path should skip tenant validation.
        Uses EXACT match for "/" so we don't accidentally whitelist all paths.
        Uses PREFIX match for /admin/, /api/auth/, etc.
        """
        if path in self.PUBLIC_EXACT_PATHS:
            return True
        return any(path.startswith(prefix) for prefix in self.PUBLIC_PATH_PREFIXES)

    def _is_superuser_request(self, request) -> bool:
        """
        Peek at the JWT in the Authorization header to check if the caller is
        a Django admin (is_staff or is_superuser).

        WHY we do this in middleware:
          TenantMiddleware runs BEFORE DRF's authentication layer. We need to
          decide whether to require a tenant code before the request reaches
          any view. Decoding the JWT here is the only way to identify admins
          at this stage without running the full DRF auth cycle.

        This is read-only — we only inspect the token, we don't set request.user.
        DRF sets request.user later inside the view dispatch.
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

        # ── Step 1: Public routes bypass all tenant logic ─────────────────────
        if self.is_public_path(request.path):
            request.tenant = None
            set_current_tenant(None)
            return self.get_response(request)

        # ── Step 2: Read the tenant code from the request header ──────────────
        # The frontend api.js interceptor adds this header automatically
        # from localStorage after login.
        tenant_code = (
            request.headers.get("X-Tenant-Code")
            or request.META.get("HTTP_X_TENANT_CODE", "")
        ).strip()

        # ── Step 3: No tenant code present ───────────────────────────────────
        if not tenant_code:
            # Admin users (is_staff / is_superuser) have no tenant.
            # They are allowed through — their ViewSets use Model.unscoped.all()
            # to see all data across all tenants.
            if self._is_superuser_request(request):
                request.tenant = None
                set_current_tenant(None)
                return self.get_response(request)

            # Non-admin request with no tenant code → reject with a clear error.
            # The frontend should never reach this state after a proper login.
            return JsonResponse(
                {"error": "X-Tenant-Code header is required for this endpoint."},
                status=400,
            )

        # ── Step 4: Validate the tenant code against the database ─────────────
        try:
            tenant = Tenant.objects.get(code=tenant_code, active=True)
        except Tenant.DoesNotExist:
            return JsonResponse(
                {"error": f"Tenant code '{tenant_code}' is invalid or the firm is inactive."},
                status=400,
            )

        # ── Step 5: Bind tenant to request and thread-local context ───────────
        # request.tenant is used by ViewSets directly.
        # set_current_tenant() is used by TenantManager in every DB query
        # to automatically filter results to this tenant's data.
        request.tenant = tenant
        set_current_tenant(tenant)

        return self.get_response(request)
