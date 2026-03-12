# apps/lawfirms/models.py

from django.db import models
from apps.core.models import BaseModel
from apps.tenants.models import Tenant
from apps.tenants.context import get_current_tenant


class LawFirm(BaseModel):
    tenant  = models.OneToOneField(Tenant, on_delete=models.CASCADE, related_name="law_firm")
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
    A legal case that progresses through workflow steps chosen by the attorney.

    LIFECYCLE:
      1. Attorney creates a case and selects a workflow_template.
         → save() detects this and auto-places the case on step 1.
         → status = step 1 name (e.g. "Initial Consultation")

      2. Attorney reviews the case situation and looks at available transitions:
         GET /api/cases/{id}/workflow_status/
         → Returns a list like:
             "Proceed to Document Collection"  (transition id 3)
             "Close Case - No Merit"           (transition id 4)

      3. Attorney picks the appropriate option:
         POST /api/cases/{id}/advance_step/
         Body: {"transition_id": 3}
         → Case moves to "Document Collection". Status updates.

      4. Repeat until the case reaches a final step (e.g. "Closed").

    RULES:
      - Never set current_step or status manually.
      - Always use WorkflowEngine.advance() or the API endpoint.
      - status always mirrors current_step.name — it is synced automatically.
    """
    law_firm = models.ForeignKey(LawFirm, on_delete=models.CASCADE, related_name="cases")
    client   = models.ForeignKey(Client,  on_delete=models.CASCADE, related_name="cases")

    code   = models.CharField(max_length=100)
    title  = models.CharField(max_length=255)
    status = models.CharField(max_length=100, default="OPEN")

    start_date = models.DateField(auto_now_add=True)
    end_date   = models.DateField(null=True, blank=True)

    workflow_template = models.ForeignKey(
        "workflows.WorkflowTemplate",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="cases",
        help_text="The workflow this case follows. Saving this auto-places the case on step 1.",
    )
    current_step = models.ForeignKey(
        "workflows.WorkflowStep",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="cases_at_this_step",
        help_text="Managed automatically. Do not edit directly.",
    )

    class Meta:
        unique_together = ("law_firm", "code")

    def save(self, *args, **kwargs):
        """
        Auto-behaviour:
          - When workflow_template is set and current_step is empty,
            place the case on step 1 of that workflow.
          - Sync status to current_step.name whenever current_step is set.
        """
        # Place on step 1 when workflow is first assigned
        if self.workflow_template_id and not self.current_step_id:
            from apps.workflows.models import WorkflowStep
            first_step = (
                WorkflowStep.unscoped
                .filter(workflow_id=self.workflow_template_id)
                .order_by("order")
                .first()
            )
            if first_step:
                self.current_step = first_step

        # Sync status
        if self.current_step:
            self.status = self.current_step.name
        elif not self.status:
            self.status = "OPEN"

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.code} — {self.title} [{self.status}]"


class Document(models.Model):
    """
    A file attached to a case.
    Plain model (no BaseModel) — tenant safety enforced in save().
    """
    case         = models.ForeignKey(Case, on_delete=models.CASCADE, related_name="documents")
    filename     = models.CharField(max_length=255)
    key          = models.CharField(max_length=255)
    content_type = models.CharField(max_length=100)
    uploaded_at  = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        tenant = get_current_tenant()
        if not tenant:
            raise PermissionError("Tenant context missing.")
        if self.case.law_firm.tenant != tenant:
            raise PermissionError("Cannot attach a document to a case outside your tenant.")
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.filename} (Case: {self.case.code})"