from django.db import models

# Create your models here.
from django.db import models
from apps.core.models import BaseModel
from apps.tenants.models import Tenant
from apps.tenants.context import get_current_tenant
from django.core.exceptions import ValidationError

class LawFirm(BaseModel):
    tenant = models.OneToOneField(
        Tenant,
        on_delete=models.CASCADE,
        related_name="law_firm"
    )

    name = models.CharField(max_length=255)
    code = models.CharField(max_length=50, unique=True)
    address = models.TextField(null=True, blank=True)
    active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.name} ({self.code})"

class Attorney(BaseModel):
    user = models.OneToOneField(
        "users.User", on_delete=models.CASCADE
    )
    law_firm = models.ForeignKey(
        LawFirm, on_delete=models.CASCADE, related_name="attorneys"
    )
    title = models.CharField(max_length=100, null=True, blank=True)
    active = models.BooleanField(default=True)

    def __str__(self):
        return self.user.username

class Client(BaseModel):
    law_firm = models.ForeignKey(
        LawFirm, on_delete=models.CASCADE, related_name="clients"
    )
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField(null=True, blank=True)
    phone = models.CharField(max_length=50, null=True, blank=True)

    def __str__(self):
        return f"{self.first_name} {self.last_name}"

class Case(BaseModel):
    law_firm = models.ForeignKey(
        LawFirm, on_delete=models.CASCADE, related_name="cases"
    )
    client = models.ForeignKey(
        Client, on_delete=models.CASCADE, related_name="cases"
    )

    case_number = models.CharField(max_length=100)
    title = models.CharField(max_length=255)

    status = models.CharField(max_length=50, default="OPEN")

    start_date = models.DateField(auto_now_add=True)
    end_date = models.DateField(null=True, blank=True)

    workflow_template = models.ForeignKey(
        "workflows.WorkflowTemplate",
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    class Meta:
        unique_together = ("law_firm", "case_number")

    def clean(self):
        """
        Ensure workflow_template belongs to same tenant as law_firm.
        """
        if self.workflow_template:
            if self.workflow_template.tenant != self.law_firm.tenant:
                raise ValidationError(
                    "WorkflowTemplate must belong to the same tenant as the LawFirm."
                )

    def save(self, *args, **kwargs):
        self.full_clean()  #ensures clean() runs
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.case_number} - {self.title}"

class Document(models.Model):
    case = models.ForeignKey("lawfirms.Case", on_delete=models.CASCADE)
    filename = models.CharField(max_length=255)
    key = models.CharField(max_length=255)
    content_type = models.CharField(max_length=100)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        from apps.tenants.context import get_current_tenant
        current_tenant = get_current_tenant()
        if not current_tenant:
            raise PermissionError("Tenant context missing")

        if self.case.law_firm.tenant != current_tenant:
            raise PermissionError("Cannot attach document to a case outside your tenant")
        super().save(*args, **kwargs)