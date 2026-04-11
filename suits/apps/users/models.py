# apps/users/models.py

from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    ROLE_CHOICES = [
        ("admin", "Admin"),
        ("lawyer", "Lawyer"),
        ("assistant", "Assistant"),
        ("client", "Client"),
    ]

    tenant = models.ForeignKey(
        "tenants.Tenant",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        db_index=True,
    )

    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default="client",
        db_index=True,
    )

    def is_admin(self):
        return self.role == "admin"

    def is_lawyer(self):
        return self.role == "lawyer"

    def is_assistant(self):
        return self.role == "assistant"

    def is_client(self):
        return self.role == "client"
