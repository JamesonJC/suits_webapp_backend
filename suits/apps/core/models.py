from django.db import models

# Create your models here.
from django.db import models
from apps.core.managers import TenantManager
from apps.tenants.context import get_current_tenant

class BaseModel(models.Model):
    tenant = models.ForeignKey(
        "tenants.Tenant",
        on_delete=models.CASCADE
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = TenantManager()

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        if not self.tenant_id:
            tenant = get_current_tenant()
            if not tenant:
                raise Exception("Tenant context missing")
            self.tenant = tenant

        super().save(*args, **kwargs)