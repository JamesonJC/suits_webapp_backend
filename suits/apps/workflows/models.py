# apps/workflows/models.py

from django.db import models
from apps.core.models import BaseModel


class WorkflowTemplate(BaseModel):
    """
    A reusable workflow blueprint for a tenant.
    BaseModel provides: tenant FK, created_at, updated_at, TenantManager, unscoped.
    """
    name        = models.CharField(max_length=255)
    description = models.TextField(null=True, blank=True)
    active      = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.name} ({self.tenant.code})"


class WorkflowStep(BaseModel):
    """
    A single step/node in a workflow template.

    Fields:
      name                — shown in admin and stored on Case.status
      description         — optional notes
      order               — integer position (unique per workflow)
      requires_attachment — blocks progression until a file is uploaded

    NOTE: step_type was removed. It was never migrated to the DB so every
    makemigrations run tried to drop it and crashed. Use description to
    annotate step purpose instead.
    """
    workflow = models.ForeignKey(
        WorkflowTemplate,
        on_delete=models.CASCADE,
        related_name="steps",
    )
    name                = models.CharField(max_length=255)
    description         = models.TextField(null=True, blank=True)
    order               = models.PositiveIntegerField()
    requires_attachment = models.BooleanField(default=False)

    class Meta:
        unique_together = ("workflow", "order")
        ordering        = ["order"]

    def __str__(self):
        return f"{self.workflow.name} — Step {self.order}: {self.name}"


class WorkflowTransition(BaseModel):
    """
    A directed edge between two steps — enables branching.

    If condition_field + condition_value are set, this transition only fires
    when context[condition_field] == condition_value.
    Leave both blank for a default/fallback transition.

    priority: lower number = evaluated first.
    """
    from_step = models.ForeignKey(
        WorkflowStep,
        on_delete=models.CASCADE,
        related_name="outgoing_transitions",
    )
    to_step = models.ForeignKey(
        WorkflowStep,
        on_delete=models.CASCADE,
        related_name="incoming_transitions",
    )
    label           = models.CharField(max_length=100, default="")
    condition_field = models.CharField(max_length=100, null=True, blank=True)
    condition_value = models.CharField(max_length=255, null=True, blank=True)
    priority        = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["priority"]

    def __str__(self):
        cond = ""
        if self.condition_field and self.condition_value:
            cond = f" [if {self.condition_field}={self.condition_value}]"
        return f"{self.from_step.name} → {self.to_step.name} ({self.label}){cond}"

    def matches(self, context: dict) -> bool:
        if not self.condition_field or not self.condition_value:
            return True
        return str(context.get(self.condition_field, "")) == str(self.condition_value)