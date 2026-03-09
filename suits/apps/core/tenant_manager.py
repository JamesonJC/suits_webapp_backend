'''from django.db import models
from apps.tenants.context import get_current_tenant
from .tenant_queryset import TenantQuerySet
from threading import local

# Thread-local storage to pass request to manager
_thread_locals = local()

def set_request(request):
    _thread_locals.request = request

def get_request():
    return getattr(_thread_locals, "request", None)


class TenantManager(models.Manager):
    """
    Manager that filters by tenant but lets superusers see all objects in Django Admin.
    """

    def get_queryset(self):
        qs = TenantQuerySet(self.model, using=self._db)
        tenant = get_current_tenant()
        request = get_request()

        # If request exists and user is superuser → return all
        if request and getattr(request.user, "is_superuser", False):
            return qs.all()

        # Normal tenant filtering
        if tenant:
            if hasattr(self.model, "tenant"):
                return qs.filter(tenant=tenant)
            if hasattr(self.model, "law_firm"):
                return qs.filter(law_firm__tenant=tenant)

        # No tenant context → empty queryset
        return qs.none()'''
from django.db import models

class TenantManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset()