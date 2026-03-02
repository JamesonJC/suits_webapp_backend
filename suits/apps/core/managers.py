from django.db import models
from apps.tenants.context import get_current_tenant

class TenantQuerySet(models.QuerySet):

    def _filter_by_tenant(self):
        tenant = get_current_tenant()
        if tenant:
            return super().filter(tenant=tenant)
        return super()

    def all(self):
        return self._filter_by_tenant()

    def filter(self, *args, **kwargs):
        qs = super().filter(*args, **kwargs)
        return qs._filter_by_tenant()

    def get(self, *args, **kwargs):
        return self._filter_by_tenant().get(*args, **kwargs)

class TenantManager(models.Manager):

    def get_queryset(self):
        tenant = get_current_tenant()
        qs = super().get_queryset()
        if tenant:
            return qs.filter(tenant=tenant)
        return qs.none()  # Safety: no tenant = no data