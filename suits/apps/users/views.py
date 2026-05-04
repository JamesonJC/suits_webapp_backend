# apps/users/views.py
#
# ─────────────────────────────────────────────────────────────────────────────
# WHY THIS FILE EXISTS AND WHAT IT FIXES:
#
#  PROBLEM 1 — Wrong view registered in urls.py:
#    The old config/urls.py pointed /api/auth/login/ at simplejwt's built-in
#    TokenObtainPairView. That view:
#      - Expects field "username" — but authService.js sends "login"
#      - Returns ONLY {access, refresh} — no user object at all
#    Result: authService.js threw "User data not returned from login." and
#    stored no tenant_code, no is_staff, no user — breaking every page.
#
#  PROBLEM 2 — Admin users got 403 on every API call:
#    After the JWT-first fix in settings.py, admin requests no longer trigger
#    CSRF. But without is_staff in the login response, the frontend treated
#    admins as firm users, stored "" as tenant_code, and sent no X-Tenant-Code.
#    Middleware then called _is_superuser_request() — which works — but the
#    frontend was already broken before that because login itself was failing.
#
#  WHAT THIS LoginView DOES:
#    - Accepts POST { login: "email_or_username", password: "..." }
#    - Finds user by email OR username (case-insensitive)
#    - Returns {access, refresh, user: {id, email, first_name, last_name,
#              is_staff, is_superuser, tenant_code, tenant_name}}
#    - tenant_code/tenant_name are resolved by walking: user→attorney→law_firm→tenant
#    - For admin users, tenant_code is null (they have no tenant)
#    - authService.js then stores "" for admins, the real code for firm users
#
#  MeView:
#    - GET /api/auth/me/ — returns same user shape for page-refresh rehydration
# ─────────────────────────────────────────────────────────────────────────────

from django.contrib.auth import get_user_model
from rest_framework.views       import APIView
from rest_framework.response    import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework             import status
from rest_framework_simplejwt.tokens import RefreshToken

User = get_user_model()


# ── Helper ────────────────────────────────────────────────────────────────────
def _resolve_tenant(user):
    """
    Walk the FK chain user → attorney → law_firm → tenant.
    Returns the Tenant instance, or None if the user has no attorney profile
    (e.g. a Django superuser or staff member who is not an attorney).

    We try the direct user.tenant attribute first in case the model has one,
    then fall back to the attorney relation.
    """
    # Direct relation (if your User model has a tenant FK — optional)
    tenant = getattr(user, "tenant", None)
    if tenant:
        return tenant

    # Attorney → law_firm → tenant chain
    try:
        return user.attorney.law_firm.tenant
    except Exception:
        return None


# ── LoginView ─────────────────────────────────────────────────────────────────
class LoginView(APIView):
    """
    POST /api/auth/login/

    Request body:
        {
            "login":    "user@example.com"   (email OR username)
            "password": "secret"
        }

    Success 200 response:
        {
            "access":  "<JWT access token>",
            "refresh": "<JWT refresh token>",
            "user": {
                "id":           1,
                "username":     "abigailcox1601",
                "email":        "abigail@example.com",
                "first_name":   "Abigail",
                "last_name":    "Cox",
                "is_staff":     false,
                "is_superuser": false,
                "tenant_code":  "FIRM001",   ← null for admins
                "tenant_name":  "Cox & Partners"  ← null for admins
            }
        }

    Error 400 responses (field + message so the form can highlight the right field):
        {"field": "login",    "message": "No account found…"}
        {"field": "password", "message": "Incorrect password."}
    """
    permission_classes = [AllowAny]   # No JWT required — this IS the login endpoint

    def post(self, request):
        login_input = (request.data.get("login") or "").strip()
        password    = (request.data.get("password") or "").strip()

        # ── Validate that both fields were provided ──────────────────────────
        if not login_input or not password:
            return Response(
                {"field": "login", "message": "Email/username and password are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # ── Look up the user by email (if "@" present) or by username ────────
        user = None
        if "@" in login_input:
            # Email lookup — case-insensitive
            user = User.objects.filter(email__iexact=login_input).first()
        if not user:
            # Username lookup — case-insensitive fallback
            user = User.objects.filter(username__iexact=login_input).first()

        if not user:
            return Response(
                {
                    "field":   "login",
                    "message": "No account found with that email or username.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # ── Verify the password ──────────────────────────────────────────────
        if not user.check_password(password):
            return Response(
                {"field": "password", "message": "Incorrect password. Please try again."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # ── Check the account is active ──────────────────────────────────────
        if not user.is_active:
            return Response(
                {
                    "field":   "login",
                    "message": "This account has been deactivated. Contact your administrator.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # ── Resolve the user's tenant (null for superusers/staff) ────────────
        tenant = _resolve_tenant(user)

        # ── Generate JWT tokens ──────────────────────────────────────────────
        refresh = RefreshToken.for_user(user)

        return Response(
            {
                "access":  str(refresh.access_token),
                "refresh": str(refresh),
                "user": {
                    "id":           user.id,
                    "username":     user.username,
                    "email":        user.email,
                    "first_name":   user.first_name,
                    "last_name":    user.last_name,
                    # ← These two let authService.js skip tenant logic for admins
                    "is_staff":     user.is_staff,
                    "is_superuser": user.is_superuser,
                    # ← Stored as X-Tenant-Code header on all subsequent requests
                    "tenant_code":  tenant.code if tenant else None,
                    "tenant_name":  tenant.name if tenant else None,
                },
            },
            status=status.HTTP_200_OK,
        )


# ── MeView ────────────────────────────────────────────────────────────────────
class MeView(APIView):
    """
    GET /api/auth/me/

    Returns the same user shape as LoginView but for the currently
    authenticated user. The frontend calls this on page refresh to
    re-hydrate the UserContext if localStorage was cleared.

    This endpoint lives under /api/auth/ which is whitelisted in
    TenantMiddleware — it never needs an X-Tenant-Code header.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user   = request.user
        tenant = _resolve_tenant(user)

        return Response({
            "id":           user.id,
            "username":     user.username,
            "email":        user.email,
            "first_name":   user.first_name,
            "last_name":    user.last_name,
            "is_staff":     user.is_staff,
            "is_superuser": user.is_superuser,
            "tenant_code":  tenant.code if tenant else None,
            "tenant_name":  tenant.name if tenant else None,
        })
