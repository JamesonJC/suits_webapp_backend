from django.db import models

# Create your models here.
from django.db import models
from apps.core.models import BaseModel

class WorkflowTemplate(BaseModel):
    name = models.CharField(max_length=100)
    version = models.IntegerField()
    status = models.CharField(max_length=20)  # DRAFT, ACTIVE

class WorkflowStep(BaseModel):
    workflow_template = models.ForeignKey(
        WorkflowTemplate,
        on_delete=models.CASCADE,
        related_name="steps"
    )
    step_name = models.CharField(max_length=100)
    step_order = models.IntegerField()
    requires_attachment = models.BooleanField(default=False)
    requires_approval = models.BooleanField(default=False)