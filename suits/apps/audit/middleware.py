from .context import set_current_user, set_current_ip

class AuditMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        set_current_user(
            request.user if request.user.is_authenticated else None
        )

        ip = request.META.get("REMOTE_ADDR")
        set_current_ip(ip)

        return self.get_response(request)