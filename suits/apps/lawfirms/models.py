# apps/lawfirms/models.py

from django.db import models
from django.core.exceptions import ValidationError

from apps.core.models import BaseModel
from apps.tenants.models import Tenant
from apps.tenants.context import get_current_tenant


class LawFirm(BaseModel):
    tenant = models.OneToOneField(
        Tenant,
        on_delete=models.CASCADE,
        related_name="law_firm",
    )
    name    = models.CharField(max_length=255)
    code    = models.CharField(max_length=50, unique=True)
    address = models.TextField(null=True, blank=True)
    active  = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.name} ({self.code})"


class Attorney(BaseModel):
    user     = models.OneToOneField("users.User", on_delete=models.CASCADE)
    law_firm = models.ForeignKey(LawFirm, on_delete=models.CASCADE, related_name="attorneys")
    title    = models.CharField(max_length=100, null=True, blank=True)
    active   = models.BooleanField(default=True)

    def __str__(self):
        return self.user.username


class Client(BaseModel):
    law_firm   = models.ForeignKey(LawFirm, on_delete=models.CASCADE, related_name="clients")
    first_name = models.CharField(max_length=100)
    last_name  = models.CharField(max_length=100)
    email      = models.EmailField(null=True, blank=True)
    phone      = models.CharField(max_length=50, null=True, blank=True)

    def __str__(self):
        return f"{self.first_name} {self.last_name}"


class Case(BaseModel):
    """
    A legal case belonging to a law firm and client.

    Workflow integration:
      - `workflow_template`  the template (blueprint) assigned to this case
      - `current_step`       the WorkflowStep the case is currently on
      - `status`             always mirrors current_step.name automatically
                             defaults to "OPEN" when no step is assigned

    To move a case through its workflow use CaseWorkflowService (services.py).
    Never update current_step or status manually — always go through the service.
    """
    law_firm = models.ForeignKey(
        LawFirm, on_delete=models.CASCADE, related_name="cases"
    )
    client = models.ForeignKey(
        Client, on_delete=models.CASCADE, related_name="cases"
    )

    # 'code' is the human-readable case identifier, e.g. "2024-PI-001"
    # unique per law firm so two firms can share the same code safely
    code   = models.CharField(max_length=100)
    title  = models.CharField(max_length=255)
    status = models.CharField(max_length=50, default="OPEN")

    start_date = models.DateField(auto_now_add=True)
    end_date   = models.DateField(null=True, blank=True)

    # The workflow blueprint — optional, assigned by attorney or admin
    workflow_template = models.ForeignKey(
        "workflows.WorkflowTemplate",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="cases",
    )

    # ✅ NEW: tracks exactly which step the case is currently on
    # When this changes, status is auto-updated in save()
    current_step = models.ForeignKey(
        "workflows.WorkflowStep",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="cases_at_this_step",
    )

    class Meta:
        unique_together = ("law_firm", "code")

    def clean(self):
        """Ensure workflow_template belongs to same tenant as law_firm."""
        if self.workflow_template:
            if self.workflow_template.tenant != self.law_firm.tenant:
                raise ValidationError(
                    "WorkflowTemplate must belong to the same tenant as the LawFirm."
                )
        if self.current_step and self.workflow_template:
            if self.current_step.workflow != self.workflow_template:
                raise ValidationError(
                    "current_step must belong to this case's workflow_template."
                )

    def save(self, *args, **kwargs):
        self.full_clean()
        # ✅ Auto-sync status to current step name.
        # This means status always reflects where the case is in the workflow.
        if self.current_step:
            self.status = self.current_step.name
        elif not self.status:
            self.status = "OPEN"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.code} - {self.title}"


class Document(models.Model):
    """
    A file attached to a case. Plain model — no tenant FK.
    Tenant safety is enforced in save() by comparing case.law_firm.tenant.
    """
    case         = models.ForeignKey("lawfirms.Case", on_delete=models.CASCADE)
    filename     = models.CharField(max_length=255)
    key          = models.CharField(max_length=255)
    content_type = models.CharField(max_length=100)
    uploaded_at  = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        current_tenant = get_current_tenant()
        if not current_tenant:
            raise PermissionError("Tenant context missing")
        if self.case.law_firm.tenant != current_tenant:
            raise PermissionError("Cannot attach document to a case outside your tenant")
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.filename} (Case: {self.case.code})"