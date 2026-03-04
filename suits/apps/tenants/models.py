from django.db import models


class Tenant(models.Model):
    """
    Represents a logical tenant (organization owner).
    Every LawFirm belongs to exactly one Tenant.
    """

    name = models.CharField(max_length=100)

    code = models.CharField(
        max_length=50,
        unique=True
    )

    active = models.BooleanField(default=True)

    #created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({self.code})"