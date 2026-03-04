# apps/lawfirms/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ClientViewSet, CaseViewSet, DocumentViewSet

router = DefaultRouter()
router.register(r"clients", ClientViewSet, basename="client")
router.register(r"cases", CaseViewSet, basename="case")
router.register(r"documents", DocumentViewSet, basename="document")

urlpatterns = [
    path("", include(router.urls)),
]