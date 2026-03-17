from django.shortcuts import render

# Create your views here.

from django.http import JsonResponse
from django.views.decorators.http import require_GET

@require_GET
def api_root(request):
  return JsonResponse({
    "message": "Suits API Backend",
    "Version": "",
    "endpoints": {
      "admin": "/admin/",
      "api": "/api/",
      "auth": "/api/auth/login",
      "token_refresh": "/api/auth/refresh",
      "tenants": "/api/tenants",
      "lawfirms": "/api/lawfirms",
      "attorneys": "/api/attorneys",
      "clients": "/api/clients",
      "cases": "/api/cases",
      "documents": "/api/documents",
      "users": "/api/users",
      "cases": "/api/cases",
      "workflows": "/api/workflows-templates",
      "workflowSteps": "/api/steps",
      "workflowTransitions": "/api/transitions",
    }
  })

