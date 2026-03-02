from django.db import models

# Create your models here.
from django.db import models
from apps.core.models import BaseModel

class AuditLog(BaseModel):
    ACTION_CHOICES = (
        ("CREATE", "Create"),
        ("UPDATE", "Update"),
        ("DELETE", "Delete"),
        ("TRANSITION", "Workflow Transition"),
        ("LOGIN", "Login"),
        ("PERMISSION_CHANGE", "Permission Change"),
    )

    actor = models.ForeignKey(
        "users.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    action = models.CharField(max_length=50, choices=ACTION_CHOICES)

    entity_type = models.CharField(max_length=100)
    entity_id = models.IntegerField()

    before = models.JSONField(null=True, blank=True)
    after = models.JSONField(null=True, blank=True)

    ip_address = models.GenericIPAddressField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]