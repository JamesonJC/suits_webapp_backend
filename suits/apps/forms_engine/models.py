# apps/forms_engine/models.py

from django.db import models
from apps.core.models import BaseModel
from apps.workflows.models import WorkflowStep
from apps.lawfirms.models import Case


class FormTemplate(BaseModel):
    """
    A form blueprint tied to a specific workflow step.
    When a job reaches that step, the attorney fills in this form.

    BaseModel already provides: tenant FK, created_at, updated_at, TenantManager.
    ✅ FIX: The original declared `tenant = ForeignKey("tenants.Tenant", ...)` again
            here. Redeclaring a field that BaseModel already provides overrides the
            TenantManager and causes duplicate tenant FK issues in migrations.
            Removed the redeclaration.
    """
    name = models.CharField(max_length=100)
    workflow_step = models.ForeignKey(
        WorkflowStep,
        on_delete=models.CASCADE,
        related_name="form_templates",
    )

    def __str__(self):
        return f"{self.name} (step: {self.workflow_step.name})"


class FormField(BaseModel):
    """
    A single field definition within a FormTemplate.
    `type` controls what input widget the frontend renders.
    `options` holds choices for select/radio/checkbox fields as a JSON list.
    """
    FIELD_TYPE_CHOICES = [
        ("text",     "Text"),
        ("number",   "Number"),
        ("date",     "Date"),
        ("select",   "Select"),
        ("checkbox", "Checkbox"),
        ("textarea", "Textarea"),
    ]

    template = models.ForeignKey(
        FormTemplate,
        on_delete=models.CASCADE,
        related_name="fields",
    )
    name     = models.CharField(max_length=100)
    type     = models.CharField(max_length=50, choices=FIELD_TYPE_CHOICES)
    required = models.BooleanField(default=False)
    options  = models.JSONField(null=True, blank=True)

    def __str__(self):
        return f"{self.template.name} → {self.name} ({self.type})"


class CaseFormSubmission(BaseModel):
    """
    A submitted (filled-in) instance of a FormTemplate for a specific case.
    `data` stores key-value pairs: field_name → submitted_value.
    """
    case = models.ForeignKey(
        Case,
        on_delete=models.CASCADE,
        related_name="form_submissions",
    )
    template = models.ForeignKey(
        FormTemplate,
        on_delete=models.CASCADE,
    )
    data         = models.JSONField()
    submitted_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Submission for {self.case.case_number} / {self.template.name}"