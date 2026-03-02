from django.contrib import admin

# Register your models here.
from django.contrib import admin
from .models import WorkflowTemplate

@admin.register(WorkflowTemplate)
class WorkflowTemplateAdmin(admin.ModelAdmin):
    list_display = ('name', 'tenant', 'created_at')
    search_fields = ('name',)
    list_filter = ('tenant',)