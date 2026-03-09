# Generated migration — adds branching support to workflows
# Changes:
#   1. WorkflowStep: adds step_type, description, requires_attachment
#   2. WorkflowTransition: new model for branching logic

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        # Depends on the existing initial workflow migration
        ("workflows", "0001_initial"),
        ("tenants", "0001_initial"),
    ]

    operations = [
        # ---- 1. Add `description` to WorkflowStep ----
        migrations.AddField(
            model_name="workflowstep",
            name="description",
            field=models.TextField(blank=True, null=True),
        ),

        # ---- 2. Add `step_type` to WorkflowStep ----
        # Defaults to LINEAR so existing steps are unaffected
        migrations.AddField(
            model_name="workflowstep",
            name="step_type",
            field=models.CharField(
                choices=[
                    ("LINEAR", "Linear"),
                    ("BRANCH", "Branch / Decision"),
                    ("END", "End"),
                ],
                default="LINEAR",
                max_length=20,
            ),
        ),

        # ---- 3. Add `requires_attachment` to WorkflowStep ----
        # Defaults to False so existing steps are unaffected
        migrations.AddField(
            model_name="workflowstep",
            name="requires_attachment",
            field=models.BooleanField(default=False),
        ),

        # ---- 4. Create WorkflowTransition model ----
        migrations.CreateModel(
            name="WorkflowTransition",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                # The condition string (e.g. "APPROVED", "REJECTED", or "" for default)
                (
                    "condition_label",
                    models.CharField(blank=True, default="", max_length=100),
                ),
                # Mark one transition as the default for linear steps
                ("is_default", models.BooleanField(default=False)),
                # The step this transition departs from
                (
                    "from_step",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="outgoing_transitions",
                        to="workflows.workflowstep",
                    ),
                ),
                # The step this transition arrives at
                (
                    "to_step",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="incoming_transitions",
                        to="workflows.workflowstep",
                    ),
                ),
                # WorkflowTransition extends BaseModel, so it needs tenant
                (
                    "tenant",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to="tenants.tenant",
                    ),
                ),
            ],
            options={
                # Prevents two transitions from the same step with the same condition
                "unique_together": {("from_step", "condition_label")},
            },
        ),
    ]