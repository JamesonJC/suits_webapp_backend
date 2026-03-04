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
        tenant_code = request.headers.get("X-Tenant-Code")

        if not tenant_code:
            request.tenant = None
            set_current_tenant(None)
            return self.get_response(request)

        try:
            tenant = Tenant.objects.get(code=tenant_code, active=True)
        except Tenant.DoesNotExist:
            return JsonResponse(
                {"error": "Invalid or inactive tenant"},
                status=400
            )

        request.tenant = tenant
        set_current_tenant(tenant)

        response = self.get_response(request)
        return response