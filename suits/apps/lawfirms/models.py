from django.db import models

# Create your models here.
from django.db import models
from apps.core.models import BaseModel

class LawFirm(BaseModel):
    name = models.CharField(max_length=255)
    code = models.CharField(max_length=50, unique=True)
    address = models.TextField(null=True, blank=True)
    active = models.BooleanField(default=True)

    def __str__(self):
        return self.name

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
    case_number = models.CharField(max_length=100, unique=True)
    title = models.CharField(max_length=255)
    status = models.CharField(max_length=50, default="OPEN")  # OPEN, CLOSED, PENDING
    start_date = models.DateField(auto_now_add=True)
    end_date = models.DateField(null=True, blank=True)
    workflow_template = models.ForeignKey(
        "workflows.WorkflowTemplate", on_delete=models.SET_NULL, null=True
    )

    def __str__(self):
        return f"{self.case_number} - {self.title}"

class Document(BaseModel):
    case = models.ForeignKey(
        Case, on_delete=models.CASCADE, related_name="documents"
    )
    filename = models.CharField(max_length=255)
    key = models.CharField(max_length=512)  # R2 object key
    content_type = models.CharField(max_length=100)
    uploaded_at = models.DateTimeField(auto_now_add=True)