# apps/workflows/migrations/0011_remove_workflowstep_stale_columns.py
#
# WHY RunSQL instead of RemoveField:
# is_end and is_start were added to the DB via raw SQL in migration 0007
# (PRAGMA table_info + ALTER TABLE). They were never recorded in Django's
# migration state. RemoveField requires the field to exist in the state —
# it crashes with KeyError when it doesn't.
#
# RunSQL talks directly to the DB, bypassing state tracking, so it works.
# We also check column existence first so re-running is safe.

from django.db import migrations


def drop_stale_columns(apps, schema_editor):
    conn = schema_editor.connection
    cursor = conn.cursor()

    # Get current columns on the table
    cursor.execute("PRAGMA table_info(workflows_workflowstep)")
    existing = {row[1] for row in cursor.fetchall()}

    # SQLite doesn't support DROP COLUMN directly in older versions,
    # but Django 6 / SQLite 3.35+ does. We use it if the column exists.
    if "is_end" in existing:
        cursor.execute("ALTER TABLE workflows_workflowstep DROP COLUMN is_end")

    if "is_start" in existing:
        cursor.execute("ALTER TABLE workflows_workflowstep DROP COLUMN is_start")


class Migration(migrations.Migration):

    dependencies = [
        ("workflows", "0010_simplify_workflowtransition"),
    ]

    operations = [
        migrations.RunPython(drop_stale_columns, migrations.RunPython.noop),
    ]