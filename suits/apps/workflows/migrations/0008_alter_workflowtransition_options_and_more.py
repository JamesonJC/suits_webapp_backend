# apps/workflows/migrations/0008_alter_workflowtransition_options_and_more.py
#
# Fixed version: removed the `RemoveField step_type` operation because
# that column was never actually created in the database, so SQLite
# crashes with "no such column: step_type" when trying to remove it.

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("tenants", "0001_initial"),
        ("workflows", "0007_add_missing_columns"),
    ]

    operations = [
        # Update Meta options on WorkflowTransition
        migrations.AlterModelOptions(
            name="workflowtransition",
            options={"ordering": ["priority"]},
        ),

        # Remove unique_together constraint if it exists
        migrations.AlterUniqueTogether(
            name="workflowtransition",
            unique_together=set(),
        ),

        # Add condition_field if not already added by 0007
        migrations.AddField(
            model_name="workflowtransition",
            name="condition_field",
            field=models.CharField(max_length=100, null=True, blank=True),
        ),

        # Add condition_value if not already added by 0007
        migrations.AddField(
            model_name="workflowtransition",
            name="condition_value",
            field=models.CharField(max_length=255, null=True, blank=True),
        ),

        # Add label if not already added by 0007
        migrations.AddField(
            model_name="workflowtransition",
            name="label",
            field=models.CharField(max_length=100, default=""),
            preserve_default=False,
        ),

        # Add priority if not already added by 0007
        migrations.AddField(
            model_name="workflowtransition",
            name="priority",
            field=models.PositiveIntegerField(default=0),
        ),

        # ✅ REMOVED: migrations.RemoveField(model_name="workflowstep", name="step_type")
        # step_type was never in the database (never migrated), so removing it crashes.

        # Remove old fields that were replaced by the above
        migrations.RemoveField(
            model_name="workflowtransition",
            name="condition_label",
        ),
        migrations.RemoveField(
            model_name="workflowtransition",
            name="is_default",
        ),
    ]