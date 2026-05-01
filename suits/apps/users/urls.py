# suits/apps/users/urls.py
#
# URL configuration for the users app.
# This file maps URL patterns to views within apps/users/.
#
# This is included in config/urls.py under the prefix "api/auth/",
# so the full URL becomes:  GET /api/auth/me/

from django.urls import path
from .views import MeView

urlpatterns = [
    path('me/', MeView.as_view(), name='user-me'),
]