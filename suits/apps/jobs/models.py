from django.db import models
from apps.core.models import BaseModel

class Job(BaseModel):
    workflow_template = models.ForeignKey("workflows.WorkflowTemplate", on_delete=models.CASCADE)
    current_step = models.ForeignKey("workflows.WorkflowStep", on_delete=models.SET_NULL, null=True, blank=True)
    status  = models.CharField(max_length=50)
    version = models.IntegerField(default=1)

class Attachment(BaseModel):
    job          = models.ForeignKey("Job", on_delete=models.CASCADE, related_name="attachments")
    filename     = models.CharField(max_length=255)
    key          = models.CharField(max_length=512)
    content_type = models.CharField(max_length=100)
    size         = models.BigIntegerField()
    uploaded_at  = models.DateTimeField(auto_now_add=True)

class Task(BaseModel):
    STATUS_PENDING     = 'Pending'
    STATUS_IN_PROGRESS = 'In Progress'
    STATUS_COMPLETED   = 'Completed'
    STATUS_CHOICES = [
        ('Pending', 'Pending'), ('In Progress', 'In Progress'), ('Completed', 'Completed'),
    ]
    PRIORITY_CHOICES = [('High','High'),('Medium','Medium'),('Low','Low')]
    CATEGORY_CHOICES = [
        ('Legal','Legal'),('Client','Client'),('Court','Court'),
        ('Administrative','Administrative'),('Other','Other'),
    ]

    title       = models.CharField(max_length=255)
    description = models.TextField(blank=True, default='')
    due_date    = models.DateField(null=True, blank=True)
    status      = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending')
    priority    = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='Medium')
    category    = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='Other')
    law_firm    = models.ForeignKey('lawfirms.LawFirm', on_delete=models.CASCADE, null=True, blank=True, related_name='tasks')
    case        = models.ForeignKey('lawfirms.Case', on_delete=models.SET_NULL, null=True, blank=True, related_name='tasks')
    assigned_to = models.ForeignKey('users.User', on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_tasks')

    class Meta:
        ordering = ['due_date', '-created_at']

    def __str__(self):
        return f"{self.title} [{self.status}]"