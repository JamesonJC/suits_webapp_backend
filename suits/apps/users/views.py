# apps/users/views.py
#
# ─────────────────────────────────────────────────────────────────────────────
# WHAT WAS BROKEN & WHY:
#
#   LoginView was returning only { id, username, email } in the user object.
#   The frontend needs:
#     - is_staff / is_superuser  → to detect admin and skip tenant-code logic
#     - tenant_code / tenant_name → to store in localStorage as X-Tenant-Code
#                                   for every subsequent authenticated request
#
#   Without is_staff, the frontend always assumed every user was a firm user,
#   tried to validate a tenant code, stored "" as the tenant code, and then
#   every API call was rejected by the tenant middleware with HTTP 400.
#
#   Without tenant_code, even firm users who typed the correct code had it
#   silently discarded — authService stored "" instead of the real code.
#
# WHAT WAS FIXED:
#   ✅ LoginView now resolves tenant via user → attorney → law_firm → tenant
#      (same lookup logic already in MeView)
#   ✅ LoginView now returns is_staff, is_superuser, tenant_code, tenant_name,
#      first_name, last_name in the user payload
#   ✅ MeView unchanged (it already returned the full profile)
# ─────────────────────────────────────────────────────────────────────────────

from django.contrib.auth import get_user_model
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken

User = get_user_model()


# ── Helper: find the tenant for a given user ─────────────────────────────────
def _resolve_tenant(user):
    """
    Walk the chain: user → attorney → law_firm → tenant
    Admin users may not have an attorney profile, so we return None for them.
    """
    tenant = getattr(user, "tenant", None)
    if not tenant:
        try:
            tenant = user.attorney.law_firm.tenant
        except Exception:
            tenant = None
    return tenant


# ── LoginView ─────────────────────────────────────────────────────────────────
class LoginView(APIView):
    """
    POST /api/auth/login/
    Body: { "login": "<email OR username>", "password": "..." }

    Returns 200 with full user payload including is_staff, is_superuser,
    tenant_code — all required by the frontend for routing and headers.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        login_input = request.data.get("login", "").strip()
        password    = request.data.get("password", "").strip()

        if not login_input or not password:
            return Response(
                {"field": "login", "message": "Please enter your email/username and password."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Find user by email or username
        user = None
        if "@" in login_input:
            user = User.objects.filter(email__iexact=login_input).first()
        if not user:
            user = User.objects.filter(username__iexact=login_input).first()

        if not user:
            return Response(
                {"field": "login", "message": "No account found with that email or username."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not user.check_password(password):
            return Response(
                {"field": "password", "message": "Incorrect password. Please try again."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not user.is_active:
            return Response(
                {"field": "login", "message": "This account is deactivated. Contact support."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        tenant  = _resolve_tenant(user)
        refresh = RefreshToken.for_user(user)

        return Response({
            "access":  str(refresh.access_token),
            "refresh": str(refresh),
            "user": {
                "id":           user.id,
                "username":     user.username,
                "email":        user.email,
                "first_name":   user.first_name,
                "last_name":    user.last_name,
                "is_staff":     user.is_staff,       # ← ADDED (admin detection)
                "is_superuser": user.is_superuser,   # ← ADDED (admin detection)
                "tenant_code":  tenant.code if tenant else None,  # ← ADDED
                "tenant_name":  tenant.name if tenant else None,  # ← ADDED
            },
        }, status=status.HTTP_200_OK)


# ── MeView ────────────────────────────────────────────────────────────────────
class MeView(APIView):
    """
    GET /api/auth/me/
    Returns the full profile of the currently authenticated user.
    Lives under /api/auth/ — whitelisted in TenantMiddleware (no tenant header needed).
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