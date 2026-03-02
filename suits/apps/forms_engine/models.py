from django.db import models

# Create your models here.
'''from django.db import models
from apps.core.models import BaseModel

class FormTemplate(BaseModel):
    name = models.CharField(max_length=100)
    workflow_step = models.ForeignKey(
        "workflows.WorkflowStep",
        on_delete=models.CASCADE
    )
    schema = models.JSONField()'''

    #Postgres JSONB makes this powerful******************************************************

from django.db import models
from apps.core.models import BaseModel
from apps.workflows.models import WorkflowStep
from apps.lawfirms.models import Case

class FormTemplate(BaseModel):
    name = models.CharField(max_length=100)
    workflow_step = models.ForeignKey(
        WorkflowStep,
        on_delete=models.CASCADE,
        related_name="form_templates"
    )
    tenant = models.ForeignKey(
        "tenants.Tenant",
        on_delete=models.CASCADE
    )

class FormField(BaseModel):
    template = models.ForeignKey(
        FormTemplate,
        on_delete=models.CASCADE,
        related_name="fields"
    )
    name = models.CharField(max_length=100)
    type = models.CharField(max_length=50)  # text, number, date, select
    required = models.BooleanField(default=False)
    options = models.JSONField(null=True, blank=True)  # for select/radio

class CaseFormSubmission(BaseModel):
    case = models.ForeignKey(
        Case,
        on_delete=models.CASCADE,
        related_name="form_submissions"
    )
    template = models.ForeignKey(
        FormTemplate,
        on_delete=models.CASCADE
    )
    data = models.JSONField()  # key-value of field_name → value
    submitted_at = models.DateTimeField(auto_now_add=True)