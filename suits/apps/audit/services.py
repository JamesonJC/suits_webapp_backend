from .models import AuditLog
from .context import get_current_user, get_current_ip
from apps.tenants.context import get_current_tenant

def log_action(action, instance, before=None, after=None):
    tenant = get_current_tenant()
    user = get_current_user()
    ip = get_current_ip()

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