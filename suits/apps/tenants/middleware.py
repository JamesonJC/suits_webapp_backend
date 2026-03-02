from .models import Tenant

class TenantMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        tenant_code = request.headers.get("X-Tenant-Code")
        
        if tenant_code:
            tenant = Tenant.objects.get(code=tenant_code)
            request.tenant = tenant
            set_current_tenant(tenant)
        else:
            request.tenant = None
            set_current_tenant(None)

        response = self.get_response(request)
        return response