# suits/apps/jobs/migrations/0002_task.py
#
# Migration: Create the Task model
#
# WHY THIS EXISTS:
#   The Task model was added in this session to power the Tasks view.
#   This migration creates the tasks_task table in the database.
#   It runs automatically via "python manage.py migrate" in entrypoint.sh
#   on every Render deployment, so no manual action is needed.
#
# DEPENDENCIES:
#   - jobs/0001_initial        : previous jobs app migration
#   - lawfirms/0002_initial    : needed for LawFirm and Case ForeignKeys
#   - tenants/0001_initial     : needed for the Tenant FK from BaseModel
#   - AUTH_USER_MODEL (swappable): needed for the assigned_to FK

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('jobs',      '0001_initial'),
        ('lawfirms',  '0002_initial'),
        ('tenants',   '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Task',
            fields=[
                ('id', models.BigAutoField(
                    auto_created=True, primary_key=True, serialize=False,
                )),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('title',       models.CharField(max_length=255)),
                ('description', models.TextField(blank=True, default='')),
                ('due_date',    models.DateField(blank=True, null=True)),
                ('status', models.CharField(
                    choices=[
                        ('Pending',     'Pending'),
                        ('In Progress', 'In Progress'),
                        ('Completed',   'Completed'),
                    ],
                    default='Pending', max_length=20,
                )),
                ('priority', models.CharField(
                    choices=[
                        ('High',   'High'),
                        ('Medium', 'Medium'),
                        ('Low',    'Low'),
                    ],
                    default='Medium', max_length=10,
                )),
                ('category', models.CharField(
                    choices=[
                        ('Legal',          'Legal'),
                        ('Client',         'Client'),
                        ('Court',          'Court'),
                        ('Administrative', 'Administrative'),
                        ('Other',          'Other'),
                    ],
                    default='Other', max_length=20,
                )),
                ('assigned_to', models.ForeignKey(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='assigned_tasks',
                    to=settings.AUTH_USER_MODEL,
                )),
                ('case', models.ForeignKey(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='tasks',
                    to='lawfirms.case',
                )),
                ('law_firm', models.ForeignKey(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='tasks',
                    to='lawfirms.lawfirm',
                )),
                ('tenant', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    to='tenants.tenant',
                )),
            ],
            options={
                'ordering': ['due_date', '-created_at'],
            },
        ),
    ]