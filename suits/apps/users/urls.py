# apps/users/urls.py
#
# ─────────────────────────────────────────────────────────────────────────────
# WHAT CHANGED:
#   ✅ Added LoginView registration as a backup path /api/auth/login/ here,
#      though the primary registration is in config/urls.py.
#      The main entry here is /api/auth/me/ (unchanged).
#
# URL STRUCTURE (included under "api/auth/" prefix in config/urls.py):
#   POST /api/auth/login/  → LoginView  (accepts login + password, returns user object)
#   GET  /api/auth/me/     → MeView     (returns current user's full profile)
# ─────────────────────────────────────────────────────────────────────────────

from django.urls import path
from .views import LoginView, MeView

urlpatterns = [
    # GET /api/auth/me/ — returns the full user profile for the logged-in user.
    # The frontend calls this on page refresh to re-hydrate the user object
    # if it was cleared from localStorage (e.g., after token refresh).
    path("me/", MeView.as_view(), name="user-me"),
]
