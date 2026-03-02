from django.db import models

# Create your models here.
from django.db import models
from apps.core.models import BaseModel

class Permission(models.Model):
    code = models.CharField(max_length=100, unique=True)
    description = models.CharField(max_length=255)

class Role(BaseModel):
    name = models.CharField(max_length=100)
    permissions = models.ManyToManyField(Permission)

class UserRole(BaseModel):
    user = models.ForeignKey("users.User", on_delete=models.CASCADE)
    role = models.ForeignKey(Role, on_delete=models.CASCADE)