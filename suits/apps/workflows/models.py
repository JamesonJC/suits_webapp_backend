from django.db import models
from apps.core.models import BaseModel
from apps.tenants.models import Tenant


class WorkflowTemplate(BaseModel):
    """
    Defines a reusable workflow for a tenant.
    """

    tenant = models.ForeignKey(
        Tenant,
        on_delete=models.CASCADE,
        related_name="workflow_templates"
    )

    name = models.CharField(max_length=255)
    description = models.TextField(null=True, blank=True)
    active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.name} ({self.tenant.code})"


class WorkflowStep(BaseModel):
    """
    Individual step inside a workflow template.
    """

    workflow = models.ForeignKey(
        WorkflowTemplate,
        on_delete=models.CASCADE,
        related_name="steps"
    )

    name = models.CharField(max_length=255)
    order = models.PositiveIntegerField()

    class Meta:
        unique_together = ("workflow", "order")
        ordering = ["order"]

    def __str__(self):
        return f"{self.workflow.name} - Step {self.order}: {self.name}"