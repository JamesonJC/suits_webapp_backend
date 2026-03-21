from django.shortcuts import render

# Create your views here.
# apps/users/views.py
#
# Custom JWT login endpoint that:
#   1. Accepts either email OR username in the same field
#   2. Returns specific error messages:
#      - "No account found with that email or username." (not registered)
#      - "Incorrect password." (user exists but wrong password)
#   3. Standard JWT tokens returned on success

from django.contrib.auth import get_user_model
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken

User = get_user_model()


class LoginView(APIView):
    """
    POST /api/auth/login/
    Body: { "login": "email@example.com OR username", "password": "..." }

    Returns:
      200 { access, refresh, user: { id, username, email } }
      400 { field: "login",    message: "No account found..." }
      400 { field: "password", message: "Incorrect password." }
    """
    permission_classes = [AllowAny]

    def post(self, request):
        login    = request.data.get("login", "").strip()
        password = request.data.get("password", "").strip()

        if not login or not password:
            return Response(
                {"field": "login", "message": "Please enter your email/username and password."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # ── Step 1: Find the user by email OR username ────────────────────────
        user = None

        # Try email first (if input looks like an email)
        if "@" in login:
            user = User.objects.filter(email__iexact=login).first()
        
        # Fall back to username (also catches emails that didn't match)
        if not user:
            user = User.objects.filter(username__iexact=login).first()

        # ── Step 2: User not found ────────────────────────────────────────────
        if not user:
            return Response(
                {
                    "field":   "login",
                    "message": "No account found with that email or username.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # ── Step 3: Wrong password ────────────────────────────────────────────
        if not user.check_password(password):
            return Response(
                {
                    "field":   "password",
                    "message": "Incorrect password. Please try again.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # ── Step 4: Account inactive ──────────────────────────────────────────
        if not user.is_active:
            return Response(
                {
                    "field":   "login",
                    "message": "This account has been deactivated. Please contact support.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # ── Step 5: Issue JWT tokens ──────────────────────────────────────────
        refresh = RefreshToken.for_user(user)

        return Response({
            "access":  str(refresh.access_token),
            "refresh": str(refresh),
            "user": {
                "id":       user.id,
                "username": user.username,
                "email":    user.email,
            },
        }, status=status.HTTP_200_OK)