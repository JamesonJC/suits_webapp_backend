# apps/core/managers.py

from django.db import models
from apps.tenants.context import get_current_tenant


class TenantManager(models.Manager):
    """
    Default manager for all BaseModel subclasses.

    Rules:
    - If tenant is set → enforce tenant filtering
    - If tenant is None → allow full access (admin / system context)

    Why:
    Django admin, authentication, and internal ORM operations rely on
    the default manager. Returning .none() breaks them.
    """

    def get_queryset(self):
        qs = super().get_queryset()
        tenant = get_current_tenant()

        # FIX: allow queries when no tenant (admin / system)
        if tenant is None:
            return qs

        # Normal tenant isolation
        return qs.filter(tenant_id=tenant.id)


class UnscopedManager(models.Manager):
    """
    Explicit bypass of tenant filtering.

    Useful for:
    - Admin-level API views
    - Background jobs
    - System services
    """

    def get_queryset(self):
        return super().get_queryset()