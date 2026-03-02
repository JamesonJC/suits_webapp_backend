from django.db import models

# Create your models here.
from django.db import models
from apps.core.models import BaseModel

class Job(BaseModel):
    workflow_template = models.ForeignKey(
        "workflows.WorkflowTemplate",
        on_delete=models.CASCADE
    )
    current_step = models.ForeignKey(
        "workflows.WorkflowStep",
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    status = models.CharField(max_length=50)
    version = models.IntegerField(default=1)

class Attachment(BaseModel):
    job = models.ForeignKey(
        "Job",
        on_delete=models.CASCADE,
        related_name="attachments"
    )
    filename = models.CharField(max_length=255)
    key = models.CharField(max_length=512)  # R2 object key
    content_type = models.CharField(max_length=100)
    size = models.BigIntegerField()
    uploaded_at = models.DateTimeField(auto_now_add=True)