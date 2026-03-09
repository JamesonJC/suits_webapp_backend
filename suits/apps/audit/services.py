# suits/apps/audit/services.py

from .models import AuditLog
from .context import get_current_user, get_current_ip
from apps.tenants.context import get_current_tenant


def log_action(action, instance, before=None, after=None):
    """
    Writes an audit log entry for any action on any BaseModel instance.

    Tenant resolution order:
      1. Thread-local context (set by TenantMiddleware on API requests)
      2. The instance's own tenant (fallback for admin/engine contexts where
         no middleware has run)
      3. If neither exists, skip logging rather than crashing.

    This means audit logging works correctly in:
      - API views (tenant from middleware)
      - Django admin (tenant from the object being modified)
      - Workflow engine transitions (tenant from the case)
    """

    # Try context first (normal API request path)
    tenant = get_current_tenant()

    # Fallback: pull tenant directly from the object being acted on
    if not tenant:
        tenant = getattr(instance, "tenant", None)

    # If we truly can't find a tenant, skip rather than crash the operation
    if not tenant:
        return

    user = get_current_user()
    ip = get_current_ip()

    # AuditLog extends BaseModel — its save() checks self.tenant_id.
    # Since we're passing tenant= explicitly, tenant_id will be set and
    # save() won't raise even without a thread-local tenant context.
    AuditLog.objects.create(
        tenant=tenant,
        actor=user,
        action=action,
        entity_type=instance.__class__.__name__,
        entity_id=instance.id,
        before=before,
        after=after,
        ip_address=ip,
    )