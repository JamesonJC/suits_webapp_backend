# apps/users/views.py
#
# ─────────────────────────────────────────────────────────────────────────────
# WHAT THIS FILE DOES:
#
#   LoginView  — POST /api/auth/login/
#     Accepts "login" (email OR username) + "password".
#     Returns {access, refresh, user: {is_staff, is_superuser, tenant_code, ...}}
#     The user object is what the frontend stores in localStorage to drive all
#     subsequent decisions (admin vs firm user, which tenant header to send).
#
#   MeView — GET /api/auth/me/
#     Returns the same user shape for the currently authenticated user.
#     Frontend calls this on page refresh to re-hydrate UserContext from the
#     server in case localStorage was cleared.
#
# ─────────────────────────────────────────────────────────────────────────────
# _resolve_tenant() — WHAT WAS FIXED:
#
#   Old version:
#     tenant = getattr(user, "tenant", None)
#     if tenant:
#         return tenant
#
#   Problem: `getattr(obj, "field", default)` only catches AttributeError.
#   User.tenant is a ForeignKey. If user.tenant_id is set but the referenced
#   Tenant row was deleted (without cascade completing), accessing user.tenant
#   raises Tenant.DoesNotExist — which is NOT an AttributeError. The getattr
#   default is never used and the exception propagates → 500 on login.
#
#   Fix: Access user.tenant_id (the raw integer column — no DB query, no
#   exception possible) to check if a tenant is set, THEN fetch it safely.
#   The entire function is wrapped in try/except so any unexpected DB or
#   model error returns None instead of crashing the login endpoint.
# ─────────────────────────────────────────────────────────────────────────────

from django.contrib.auth import get_user_model
from rest_framework.views       import APIView
from rest_framework.response    import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework             import status
from rest_framework_simplejwt.tokens import RefreshToken

User = get_user_model()


# ── Helper ─────────────────────────────────────────────────────────────────────
def _resolve_tenant(user):
    """
    Find the Tenant for a given user. Returns the Tenant instance or None.

    Resolution order:
      1. User.tenant_id  → direct FK on the User model (fast, no extra query)
      2. user.attorney.law_firm.tenant  → attorney profile chain (firm users)

    Both paths are wrapped in try/except so any unexpected error (deleted row,
    missing profile, broken FK) returns None instead of raising to the caller.

    Admin users (is_staff / is_superuser) typically have no tenant — None is
    the expected return value for them.
    """

    # ── Path 1: User model has a direct tenant FK ─────────────────────────────
    # Access user.tenant_id (the raw DB column integer) — this NEVER hits
    # the database and NEVER raises an exception. If it's None or missing,
    # we fall through to path 2.
    try:
        tenant_id = getattr(user, 'tenant_id', None)
        if tenant_id:
            # Now do the DB lookup safely — use .filter().first() to avoid
            # DoesNotExist if the row was deleted after tenant_id was set.
            from apps.tenants.models import Tenant
            return Tenant.objects.filter(id=tenant_id, active=True).first()
    except Exception:
        pass  # Any DB error → try the attorney chain next

    # ── Path 2: Attorney profile chain ───────────────────────────────────────
    # user.attorney → RelatedObjectDoesNotExist if no attorney profile
    # .law_firm     → could be None
    # .tenant       → the Tenant we want
    # All wrapped in one try/except so any failure returns None cleanly.
    try:
        return user.attorney.law_firm.tenant
    except Exception:
        return None


# ── LoginView ──────────────────────────────────────────────────────────────────
class LoginView(APIView):
    """
    POST /api/auth/login/

    Request body:
        { "login": "email_or_username", "password": "secret" }

    200 response:
        {
            "access":  "<JWT>",
            "refresh": "<JWT>",
            "user": {
                "id":           1,
                "username":     "abigailcox1601",
                "email":        "ab@example.com",
                "first_name":   "Abigail",
                "last_name":    "Cox",
                "is_staff":     false,
                "is_superuser": false,
                "tenant_code":  "T1",    ← null for admins
                "tenant_name":  "Cox Law" ← null for admins
            }
        }

    400 responses:
        {"field": "login",    "message": "No account found…"}
        {"field": "password", "message": "Incorrect password."}
    """
    # AllowAny — no JWT required, this IS the login endpoint
    # Middleware also passes /api/auth/ through without tenant check
    permission_classes = [AllowAny]

    def post(self, request):
        login_input = (request.data.get('login') or '').strip()
        password    = (request.data.get('password') or '').strip()

        # Validate both fields are present
        if not login_input or not password:
            return Response(
                {'field': 'login', 'message': 'Email/username and password are required.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Look up user by email first (if "@" present), then by username
        user = None
        if '@' in login_input:
            user = User.objects.filter(email__iexact=login_input).first()
        if not user:
            user = User.objects.filter(username__iexact=login_input).first()

        if not user:
            return Response(
                {'field': 'login', 'message': 'No account found with that email or username.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not user.check_password(password):
            return Response(
                {'field': 'password', 'message': 'Incorrect password. Please try again.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not user.is_active:
            return Response(
                {'field': 'login', 'message': 'This account is deactivated. Contact your administrator.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Resolve tenant — safe, returns None for admins
        tenant = _resolve_tenant(user)

        # Issue JWT tokens
        refresh = RefreshToken.for_user(user)

        return Response({
            'access':  str(refresh.access_token),
            'refresh': str(refresh),
            'user': {
                'id':           user.id,
                'username':     user.username,
                'email':        user.email,
                'first_name':   user.first_name,
                'last_name':    user.last_name,
                # Frontend uses these to detect admin and skip tenant logic
                'is_staff':     user.is_staff,
                'is_superuser': user.is_superuser,
                # Frontend stores this as X-Tenant-Code header on all API calls
                # null for admins → frontend stores "" → interceptor skips header
                'tenant_code':  tenant.code if tenant else None,
                'tenant_name':  tenant.name if tenant else None,
            },
        }, status=status.HTTP_200_OK)


# ── MeView ─────────────────────────────────────────────────────────────────────
class MeView(APIView):
    """
    GET /api/auth/me/

    Returns the full user profile for the currently authenticated user.
    Lives under /api/auth/ which middleware exempts from tenant checks.
    Frontend calls this on page refresh to re-hydrate UserContext.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user   = request.user
        tenant = _resolve_tenant(user)

        return Response({
            'id':           user.id,
            'username':     user.username,
            'email':        user.email,
            'first_name':   user.first_name,
            'last_name':    user.last_name,
            'is_staff':     user.is_staff,
            'is_superuser': user.is_superuser,
            'tenant_code':  tenant.code if tenant else None,
            'tenant_name':  tenant.name if tenant else None,
        })