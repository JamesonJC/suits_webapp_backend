"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.contrib import admin
#from django.urls import path

#urlpatterns = [
    #path("admin/", admin.site.urls),
#]
from django.urls import path
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from apps.tenants.views import TenantViewSet
from apps.workflows.views import WorkflowTemplateViewSet
from apps.lawfirms.views import LawFirmViewSet

router = DefaultRouter()

router.register(r"tenants", TenantViewSet)
#router.register(r"workflow-templates", WorkflowTemplateViewSet)
router.register(r"workflow-templates", WorkflowTemplateViewSet, basename="workflowtemplate")
router.register(r"lawfirms", LawFirmViewSet, basename="lawfirm")

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/auth/login/", TokenObtainPairView.as_view()),
    path("api/auth/refresh/", TokenRefreshView.as_view()),
    path("api/", include("apps.workflows.urls")),
    path("api/", include(router.urls)),
]