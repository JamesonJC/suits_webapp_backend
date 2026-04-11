# apps/core/managers.py

from django.db import models
from apps.tenants.context import get_current_tenant


class TenantManager(models.Manager):
    """
    Default manager for all BaseModel subclasses.
    Automatically filters every query to the current tenant stored in
    thread-local context (set by TenantMiddleware from X-Tenant-Code header).
    Returns .none() when no tenant is set — this is the safe default so
    requests without a tenant header never leak cross-tenant data.
    """

    def get_queryset(self):
        qs = super().get_queryset()
        tenant = get_current_tenant()

        if tenant is None:
            # Safe default: no tenant context → no data
            return qs.none()

        # Enforce tenant isolation
        return qs.filter(tenant_id=tenant.id)


class UnscopedManager(models.Manager):
    """
    Bypasses all tenant filtering.
    USE ONLY IN:
      - Django admin (TenantAdminMixin uses this)
      - Internal services (WorkflowEngine, seed commands, tests)
    Never expose this through API views.
    """

    def get_queryset(self):
        return super().get_queryset()
