from django.db import migrations

def add_missing_columns(apps, schema_editor):
    conn = schema_editor.connection

    def cols(table):
        c = conn.cursor()
        c.execute(f"PRAGMA table_info({table})")
        return {row[1] for row in c.fetchall()}

    step_cols = cols("workflows_workflowstep")
    if "description" not in step_cols:
        conn.cursor().execute("ALTER TABLE workflows_workflowstep ADD COLUMN description TEXT NULL")
    if "requires_attachment" not in step_cols:
        conn.cursor().execute("ALTER TABLE workflows_workflowstep ADD COLUMN requires_attachment BOOL NOT NULL DEFAULT 0")

    trans_cols = cols("workflows_workflowtransition")
    if "label" not in trans_cols:
        conn.cursor().execute("ALTER TABLE workflows_workflowtransition ADD COLUMN label VARCHAR(100) NOT NULL DEFAULT ''")
    if "condition_field" not in trans_cols:
        conn.cursor().execute("ALTER TABLE workflows_workflowtransition ADD COLUMN condition_field VARCHAR(100) NULL")
    if "condition_value" not in trans_cols:
        conn.cursor().execute("ALTER TABLE workflows_workflowtransition ADD COLUMN condition_value VARCHAR(255) NULL")
    if "priority" not in trans_cols:
        conn.cursor().execute("ALTER TABLE workflows_workflowtransition ADD COLUMN priority INTEGER NOT NULL DEFAULT 0")

class Migration(migrations.Migration):
    dependencies = [("workflows", "0006_merge_20260308_2206")]
    operations = [migrations.RunPython(add_missing_columns, migrations.RunPython.noop)]
