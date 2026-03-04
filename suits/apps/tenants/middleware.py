# apps/tenants/middleware.py
from django.http import JsonResponse
from .models import Tenant
from .context import set_current_tenant

class TenantMiddleware:
    """
    Extracts tenant from X-Tenant-Code header
    and attaches it to request + thread context.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.tenant = None
        set_current_tenant(None)

        # Support normal headers AND DRF test client headers
        tenant_code = request.headers.get("X-Tenant-Code") or request.META.get("HTTP_X_TENANT_CODE")

        if tenant_code:
            try:
                tenant = Tenant.objects.get(code=tenant_code, active=True)
            except Tenant.DoesNotExist:
                return JsonResponse({"error": "Invalid or inactive tenant"}, status=400)
            request.tenant = tenant
            set_current_tenant(tenant)

        return self.get_response(request)