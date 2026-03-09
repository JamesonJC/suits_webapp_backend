# apps/core/models.py
#
# BaseModel is the foundation for all tenant-aware models in this system.
#
# Two managers:
#   objects  — TenantManager: always filters to the current tenant (thread-local).
#              Used everywhere in views and API.
#   unscoped — UnscopedManager: no tenant filter. Used in admin and internal
#              services that need to see across all tenants.

from django.db import models
from apps.core.managers import TenantManager, UnscopedManager
from apps.tenants.context import get_current_tenant


class BaseModel(models.Model):
    tenant = models.ForeignKey(
        "tenants.Tenant",
        on_delete=models.CASCADE,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # ✅ objects: tenant-scoped — used in all API views
    objects = TenantManager()

    # ✅ unscoped: no filter — used in admin and engine internals
    unscoped = UnscopedManager()

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        # Auto-assign tenant from thread-local context if not set on new objects
        if not self.pk and not self.tenant_id:
            tenant = get_current_tenant()
            if not tenant:
                raise Exception(
                    f"Cannot save {self.__class__.__name__}: "
                    "tenant is not set and no tenant is in the current context. "
                    "Either set obj.tenant explicitly or call set_current_tenant() first."
                )
            self.tenant = tenant
        super().save(*args, **kwargs)