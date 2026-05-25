# suits/apps/jobs/migrations/0002_task.py
#
# ─────────────────────────────────────────────────────────────────────────────
# WHY THIS FILE DIDN'T EXIST (and why /api/tasks/ returned 500):
#
#   The Task model was written in jobs/models.py but this migration file
#   was never committed to the repository.
#
#   When Django processes a request to /api/tasks/, it tries to query the
#   tasks_task table. Since migrate never ran AND this file was missing,
#   the table simply didn't exist in the database.
#   PostgreSQL responded: "relation tasks_task does not exist"
#   Django turned that into HTTP 500.
#
# HOW DJANGO MIGRATIONS WORK (so you understand this):
#   1. You define a model in models.py
#   2. You run `python manage.py makemigrations` → creates this .py file
#   3. You run `python manage.py migrate` → executes the SQL (CREATE TABLE)
#   4. Django records it in the django_migrations table
#   5. Future `migrate` calls skip it (idempotent)
#
#   In our setup, step 3 happens automatically via entrypoint.sh on every deploy.
#
# DEPENDENCIES:
#   jobs/0001_initial     — previous jobs migration (must exist first)
#   lawfirms/0002_initial — provides LawFirm and Case models for ForeignKeys
#   tenants/0001_initial  — provides Tenant model (inherited from BaseModel)
#   AUTH_USER_MODEL       — swappable; resolves to users.User in this project
# ─────────────────────────────────────────────────────────────────────────────

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        # Previous migration in this app — must be applied first
        ('jobs', '0001_initial'),

        # LawFirm and Case ForeignKeys on Task
        ('lawfirms', '0002_initial'),

        # Tenant FK inherited from BaseModel
        ('tenants', '0001_initial'),

        # assigned_to FK — swappable so Django resolves it correctly
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Task',
            fields=[
                # Primary key — auto-incrementing BigInt (Django default)
                ('id', models.BigAutoField(
                    auto_created=True,
                    primary_key=True,
                    serialize=False,
                    verbose_name='ID',
                )),

                # Timestamps from BaseModel
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),

                # Core task fields
                ('title', models.CharField(max_length=255)),
                ('description', models.TextField(blank=True, default='')),
                ('due_date', models.DateField(blank=True, null=True)),

                # Status: drives the coloured circle icon in the UI
                ('status', models.CharField(
                    choices=[
                        ('Pending',     'Pending'),
                        ('In Progress', 'In Progress'),
                        ('Completed',   'Completed'),
                    ],
                    default='Pending',
                    max_length=20,
                )),

                # Priority: drives the coloured badge in the UI
                ('priority', models.CharField(
                    choices=[
                        ('High',   'High'),
                        ('Medium', 'Medium'),
                        ('Low',    'Low'),
                    ],
                    default='Medium',
                    max_length=10,
                )),

                # Category: shown as grey pill badge in the UI
                ('category', models.CharField(
                    choices=[
                        ('Legal',          'Legal'),
                        ('Client',         'Client'),
                        ('Court',          'Court'),
                        ('Administrative', 'Administrative'),
                        ('Other',          'Other'),
                    ],
                    default='Other',
                    max_length=20,
                )),

                # Optional user assigned to this task
                ('assigned_to', models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='assigned_tasks',
                    to=settings.AUTH_USER_MODEL,
                )),

                # Optional link to a specific case
                ('case', models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='tasks',
                    to='lawfirms.case',
                )),

                # Law firm scoping — filters tasks to one firm within the tenant
                ('law_firm', models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='tasks',
                    to='lawfirms.lawfirm',
                )),

                # Tenant FK — required by BaseModel, used by TenantManager
                # to auto-scope all queries to the current tenant
                ('tenant', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    to='tenants.tenant',
                )),
            ],
            options={
                # Default ordering: soonest due date first, newest created first
                'ordering': ['due_date', '-created_at'],
            },
        ),
    ]