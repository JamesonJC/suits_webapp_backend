import django.db.models.deletion
from django.db import migrations, models

class Migration(migrations.Migration):

    dependencies = [
        ("lawfirms", "0002_alter_lawfirm_tenant"),
        ("workflows", "0006_merge_20260308_2206"),
    ]

    operations = [
        migrations.AddField(
            model_name="case",
            name="current_step",
            field=models.ForeignKey(
                to="workflows.workflowstep",
                on_delete=django.db.models.deletion.SET_NULL,
                null=True,
                blank=True,
                related_name="cases_at_this_step",
                help_text="The workflow step this case is currently on.",
            ),
        ),
    ]
