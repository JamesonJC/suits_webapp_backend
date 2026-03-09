# apps/audit/models.py

from django.db import models


class AuditLog(models.Model):
    """
    An immutable record of every meaningful action in the system.

    ✅ FIX: AuditLog previously extended BaseModel.
            BaseModel.save() raises Exception("Tenant context missing") when
            tenant is None — which happens for system-level events like LOGIN
            that occur before a tenant is resolved.
            AuditLog is now a plain models.Model with its own nullable tenant FK
            and its own timestamps. It can always be written to safely.

    The nullable tenant also lets superadmin actions (no tenant context) be logged.
    """

    ACTION_CHOICES = (
        ("CREATE",            "Create"),
        ("UPDATE",            "Update"),
        ("DELETE",            "Delete"),
        ("TRANSITION",        "Workflow Transition"),
        ("LOGIN",             "Login"),
        ("PERMISSION_CHANGE", "Permission Change"),
    )

    # Nullable: system events (login, etc.) happen outside tenant context
    tenant = models.ForeignKey(
        "tenants.Tenant",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )

    actor = models.ForeignKey(
        "users.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )

    action      = models.CharField(max_length=50, choices=ACTION_CHOICES)
    entity_type = models.CharField(max_length=100)
    entity_id   = models.IntegerField()

    before     = models.JSONField(null=True, blank=True)
    after      = models.JSONField(null=True, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)

    # Own timestamps — no longer relies on BaseModel
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        actor = self.actor.username if self.actor else "system"
        return f"[{self.action}] {self.entity_type}:{self.entity_id} by {actor}"