# apps/workflows/admin.py
#
# WHY THE STEPS DROPDOWNS WERE EMPTY:
# WorkflowStep uses TenantManager. Admin has no tenant context → filter returns
# nothing. TenantAdminMixin.formfield_for_foreignkey switches every FK dropdown
# to use model.unscoped instead.

from django.contrib import admin
from apps.core.admin_mixins import TenantAdminMixin
from .models import WorkflowTemplate, WorkflowStep, WorkflowTransition


@admin.register(WorkflowTemplate)
class WorkflowTemplateAdmin(TenantAdminMixin, admin.ModelAdmin):
    list_display  = ("name", "tenant", "active", "created_at")
    search_fields = ("name",)
    list_filter   = ("tenant", "active")


@admin.register(WorkflowStep)
class WorkflowStepAdmin(TenantAdminMixin, admin.ModelAdmin):
    list_display  = ("name", "workflow", "order", "requires_attachment")
    list_filter   = ("workflow__tenant", "requires_attachment")
    search_fields = ("name", "workflow__name")
    ordering      = ("workflow", "order")


@admin.register(WorkflowTransition)
class WorkflowTransitionAdmin(TenantAdminMixin, admin.ModelAdmin):
    """
    The from_step / to_step dropdowns were empty because WorkflowStep uses
    TenantManager. TenantAdminMixin.formfield_for_foreignkey fixes this by
    switching to model.unscoped for all FK fields.
    """
    list_display  = ("from_step", "to_step", "label", "condition_field", "condition_value", "priority")
    list_filter   = ("from_step__workflow__tenant",)
    search_fields = ("label", "from_step__name", "to_step__name")
    ordering      = ("from_step__workflow", "priority")