# apps/workflows/migrations/0012_drop_all_stale_columns.py
#
# Drops every stale column that exists in the DB but not in the current models.
# These were all added via raw SQL (never tracked in Django migration state)
# so RemoveField won't work — we use RunPython + PRAGMA table_info instead.
#
# Stale columns found so far:
#   workflows_workflowstep:       is_end, is_start, requires_approval, requires_document
#   workflows_workflowtransition: requires_approval, requires_document (old fields)
#
# We check all of them and drop whichever exist, so this is safe to run
# even if some were already dropped by 0011.

from django.db import migrations


def drop_stale_columns(apps, schema_editor):
    conn = schema_editor.connection
    cursor = conn.cursor()

    def existing_columns(table):
        cursor.execute(f"PRAGMA table_info({table})")
        return {row[1] for row in cursor.fetchall()}

    # ── WorkflowStep stale columns ───────────────────────────────────────────
    step_cols = existing_columns("workflows_workflowstep")
    stale_step = ["is_end", "is_start", "requires_approval", "requires_document"]
    for col in stale_step:
        if col in step_cols:
            cursor.execute(f"ALTER TABLE workflows_workflowstep DROP COLUMN {col}")

    # ── WorkflowTransition stale columns ─────────────────────────────────────
    trans_cols = existing_columns("workflows_workflowtransition")
    stale_trans = ["requires_approval", "requires_document", "name", "order",
                   "condition_label", "is_default"]
    for col in stale_trans:
        if col in trans_cols:
            cursor.execute(f"ALTER TABLE workflows_workflowtransition DROP COLUMN {col}")


class Migration(migrations.Migration):

    dependencies = [
        ("workflows", "0011_remove_workflowstep_stale_columns"),
    ]

    operations = [
        migrations.RunPython(drop_stale_columns, migrations.RunPython.noop),
    ]