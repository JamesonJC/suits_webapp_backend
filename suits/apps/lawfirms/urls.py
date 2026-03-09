from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import LawFirmViewSet, AttorneyViewSet, ClientViewSet, CaseViewSet, DocumentViewSet

router = DefaultRouter()
router.register(r"lawfirms", LawFirmViewSet, basename="lawfirm")
router.register(r"attorneys", AttorneyViewSet, basename="attorney")
router.register(r"clients", ClientViewSet, basename="client")
router.register(r"cases", CaseViewSet, basename="case")
router.register(r"documents", DocumentViewSet, basename="document")

urlpatterns = [
    path("", include(router.urls)),
]