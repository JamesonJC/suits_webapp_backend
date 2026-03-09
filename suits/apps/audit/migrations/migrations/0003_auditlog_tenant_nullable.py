# apps/audit/migrations/0003_auditlog_tenant_nullable.py
#
# AuditLog.tenant is now nullable so system-level events (login, password reset)
# can be logged even when there is no tenant in thread context.

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("audit", "0002_initial"),
        ("tenants", "0001_initial"),
    ]

    operations = [
        migrations.AlterField(
            model_name="auditlog",
            name="tenant",
            field=models.ForeignKey(
                to="tenants.tenant",
                on_delete=django.db.models.deletion.CASCADE,
                null=True,
                blank=True,
            ),
        ),
    ]