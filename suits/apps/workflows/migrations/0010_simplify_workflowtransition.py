# apps/workflows/migrations/0010_simplify_workflowtransition.py
#
# WHY: The old WorkflowTransition had condition_field, condition_value, and priority
# for automated rule evaluation. The system is now attorney-driven: the attorney
# picks the transition they want. These fields are removed.
#
# The only fields on WorkflowTransition are now:
#   from_step, to_step, label, tenant (from BaseModel), created_at, updated_at

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("workflows", "0009_remove_workflowstep_step_type_and_more"),
    ]

    operations = [
        # Remove the automated-decision fields — not needed in attorney-driven model
        migrations.RemoveField(
            model_name="workflowtransition",
            name="condition_field",
        ),
        migrations.RemoveField(
            model_name="workflowtransition",
            name="condition_value",
        ),
        migrations.RemoveField(
            model_name="workflowtransition",
            name="priority",
        ),
        # Add unique_together so you can't have duplicate labels from the same step
        migrations.AlterUniqueTogether(
            name="workflowtransition",
            unique_together={("from_step", "label")},
        ),
    ]