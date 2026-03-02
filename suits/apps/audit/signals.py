from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.forms.models import model_to_dict
from .services import log_action

from apps.core.models import BaseModel


@receiver(post_save)
def log_model_save(sender, instance, created, **kwargs):
    if not issubclass(sender, BaseModel):
        return

    if sender.__name__ == "AuditLog":
        return

    action = "CREATE" if created else "UPDATE"

    log_action(
        action=action,
        instance=instance,
        after=model_to_dict(instance),
    )


@receiver(post_delete)
def log_model_delete(sender, instance, **kwargs):
    if not issubclass(sender, BaseModel):
        return

    log_action(
        action="DELETE",
        instance=instance,
        before=model_to_dict(instance),
    )