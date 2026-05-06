"""
apps/tenants/middleware.py — Tenant Middleware

─────────────────────────────────────────────────────────────────────────────
ROOT CAUSES FIXED IN THIS VERSION:

  BUG 1 — "/admin" (no trailing slash) was blocked:
    Old code used PREFIX matching against "/admin/" (with slash).
    "/admin".startswith("/admin/") → FALSE.
    So hitting /admin in a browser sent the request through tenant enforcement
    and returned {"error": "X-Tenant-Code header is required"} before Django's
    CommonMiddleware could redirect /admin → /admin/.

    Fix: The new logic only enforces tenant on paths that START with "/api/".
    EVERYTHING else (/, /admin, /admin/, /static/, /favicon.ico) passes through
    with no tenant check at all. No more list of prefixes to maintain.

  BUG 2 — List-of-prefixes approach was fragile:
    Any new public path (e.g. /health/, /metrics/) had to be manually added.
    The new approach is declarative: "only /api/ paths need tenant validation".
    /api/auth/ paths (login, refresh, me) are also exempt — tenant is unknown
    until after the user authenticates.

  BUG 3 — Admin bypass could hang on slow cold-start:
    _is_superuser_request() decodes the JWT every time an admin hits an
    untenanted /api/ path. Added a short-circuit: if Authorization header
    is absent, skip JWT decode entirely (unauthenticated request — reject fast).

─────────────────────────────────────────────────────────────────────────────
HOW THE LOGIC FLOWS (read this to understand every branch):

  Request arrives
      │
      ├─ Path does NOT start with "/api/"
      │   → Not an API call (admin panel, root, static, favicon, etc.)
      │   → Bypass all tenant logic. Pass through.
      │
      ├─ Path starts with "/api/auth/"
      │   → Login, refresh, me — tenant unknown at this stage
      │   → Bypass tenant logic. Pass through.
      │
      └─ Path starts with "/api/" but NOT "/api/auth/"
          → Protected API endpoint. Tenant required.
          │
          ├─ X-Tenant-Code header present and valid
          │   → Bind tenant to request. Pass through.
          │
          ├─ No X-Tenant-Code, but JWT belongs to an admin (is_staff/superuser)
          │   → Admins see all data. Bind tenant=None. Pass through.
          │   → ViewSets handle admin via Model.unscoped.all() or objects.all()
          │
          └─ No X-Tenant-Code, not an admin (or no JWT at all)
              → Return 400. Frontend should never reach this after login.
─────────────────────────────────────────────────────────────────────────────
"""

from django.http import JsonResponse
from .models import Tenant
from .context import set_current_tenant


class TenantMiddleware:

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        path = request.path

        # ── Step 1: Non-API paths → always bypass ────────────────────────────
        # This covers: /admin, /admin/, /, /static/…, /favicon.ico, etc.
        # We ONLY enforce tenant logic on /api/ paths. Everything else
        # (Django admin panel, root redirect, static assets) passes through
        # without any tenant check.
        # NOTE: This also fixes the "/admin" vs "/admin/" ambiguity — both
        # are non-/api/ paths and both bypass freely.
        if not path.startswith('/api/'):
            request.tenant = None
            set_current_tenant(None)
            return self.get_response(request)

        # ── Step 2: Public API paths → bypass ────────────────────────────────
        # /api/auth/login/, /api/auth/refresh/, /api/auth/me/
        # The user is not yet authenticated at login time, so we cannot
        # know their tenant. These endpoints set their own permissions.
        if path.startswith('/api/auth/'):
            request.tenant = None
            set_current_tenant(None)
            return self.get_response(request)

        # ── Step 3: Protected API path — read the tenant code header ─────────
        # The frontend api.js interceptor adds X-Tenant-Code from localStorage
        # on every request after login.
        tenant_code = (
            request.headers.get('X-Tenant-Code') or
            request.META.get('HTTP_X_TENANT_CODE', '')
        ).strip()

        # ── Step 4: No tenant code provided ──────────────────────────────────
        if not tenant_code:
            # Short-circuit: if there's no Authorization header at all,
            # there's no JWT to decode — skip the superuser check and reject.
            auth_header = request.headers.get('Authorization', '')
            if auth_header.startswith('Bearer ') and self._is_superuser_request(request):
                # Admin users (is_staff / is_superuser) have no tenant.
                # Their ViewSets use Model.unscoped.all() / Document.objects.all()
                # to bypass tenant filtering and see all records.
                request.tenant = None
                set_current_tenant(None)
                return self.get_response(request)

            # Non-admin with no tenant code — reject.
            # After a successful login the frontend always has this header.
            # Reaching here means the request is either:
            #   a) unauthenticated (no token at all), or
            #   b) from a firm user whose frontend bug isn't sending the header
            return JsonResponse(
                {'error': 'X-Tenant-Code header is required for this endpoint.'},
                status=400,
            )

        # ── Step 5: Validate the tenant code ─────────────────────────────────
        try:
            tenant = Tenant.objects.get(code=tenant_code, active=True)
        except Tenant.DoesNotExist:
            return JsonResponse(
                {'error': f"Tenant code '{tenant_code}' is invalid or the firm is inactive."},
                status=400,
            )

        # ── Step 6: Bind tenant to request + thread-local context ─────────────
        # request.tenant  → used directly by ViewSets
        # set_current_tenant() → used by TenantManager on every DB query to
        #                         automatically filter results to this firm only
        request.tenant = tenant
        set_current_tenant(tenant)

        return self.get_response(request)

    def _is_superuser_request(self, request) -> bool:
        """
        Peek at the JWT in the Authorization header to decide if this is an
        admin user (is_staff or is_superuser).

        WHY in middleware (not in the view):
            TenantMiddleware runs before DRF authentication. We need to decide
            whether to require X-Tenant-Code BEFORE the view runs. Decoding
            the JWT here is the only way to identify admins at this point.

        This is READ-ONLY — we only inspect the token payload.
        DRF sets request.user properly later during view dispatch.

        Returns False on any error (malformed token, expired token, etc.)
        so the request is safely rejected rather than accidentally permitted.
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