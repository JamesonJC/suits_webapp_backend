# apps/workflows/admin.py

from django.contrib import admin
from apps.core.admin_mixins import TenantAdminMixin
from apps.workflows.engine import WorkflowEngine
from .models import WorkflowTemplate, WorkflowStep, WorkflowTransition


class WorkflowStepInline(admin.TabularInline):
    """
    Add/edit steps directly on the WorkflowTemplate form.
    Tenant is inherited automatically from the parent template on save.
    """
    model    = WorkflowStep
    extra    = 1
    fields   = ("order", "name", "description", "requires_attachment")
    ordering = ("order",)

    def get_queryset(self, request):
        # Must use unscoped — no tenant context in admin
        return WorkflowStep.unscoped.all()


@admin.register(WorkflowTemplate)
class WorkflowTemplateAdmin(TenantAdminMixin, admin.ModelAdmin):
    list_display  = ("name", "tenant", "active", "step_count")
    search_fields = ("name",)
    list_filter   = ("tenant", "active")
    inlines       = [WorkflowStepInline]

    def step_count(self, obj):
        return WorkflowStep.unscoped.filter(workflow=obj).count()
    step_count.short_description = "Steps"

    def save_formset(self, request, form, formset, change):
        """
        Before saving inline steps, copy the template's tenant onto each step.

        WHY: BaseModel.save() requires tenant to be set. Admin has no tenant
        header, so thread-local context is None. Without this override every
        inline step save raises "tenant is not set".
        """
        instances = formset.save(commit=False)

        # The parent template — tenant is already set on it from the main form
        template = form.instance

        for obj in instances:
            if hasattr(obj, "tenant_id") and not obj.tenant_id:
                # Inherit tenant from the parent WorkflowTemplate
                obj.tenant = template.tenant
            obj.save()

        # Handle deletions
        for obj in formset.deleted_objects:
            obj.delete()

        formset.save_m2m()


@admin.register(WorkflowStep)
class WorkflowStepAdmin(TenantAdminMixin, admin.ModelAdmin):
    list_display  = ("name", "workflow", "order", "requires_attachment")
    list_filter   = ("workflow__tenant", "workflow")
    search_fields = ("name", "workflow__name")
    ordering      = ("workflow", "order")

    def save_model(self, request, obj, form, change):
        """Inherit tenant from the step's workflow if not already set."""
        if not obj.tenant_id and obj.workflow_id:
            # workflow is a BaseModel so it has a tenant
            obj.tenant = WorkflowStep.unscoped.filter(
                workflow_id=obj.workflow_id
            ).values_list("tenant", flat=True).first() or obj.workflow.tenant
        super().save_model(request, obj, form, change)


@admin.register(WorkflowTransition)
class WorkflowTransitionAdmin(TenantAdminMixin, admin.ModelAdmin):
    """
    Each transition is one choice an attorney can make from a step.

    from_step → the step the case is currently on
    to_step   → where this choice sends the case
    label     → what the attorney sees, e.g. "Proceed to Negotiation"

    Add multiple transitions from the same from_step to give attorneys options.

    Example — "Case Review" step:
      label: "Proceed to Negotiation"     → to_step: Negotiation
      label: "Request More Documents"     → to_step: Document Collection
      label: "Escalate to Partner Review" → to_step: Partner Review
      label: "Close - No Merit"           → to_step: Closed
    """
    list_display  = ("from_step", "label", "to_step")
    list_filter   = ("from_step__workflow__tenant", "from_step__workflow", "from_step")
    search_fields = ("label", "from_step__name", "to_step__name")
    ordering      = ("from_step__workflow", "from_step__order", "label")

    def save_model(self, request, obj, form, change):
        """Inherit tenant from the from_step's workflow if not set."""
        if not obj.tenant_id and obj.from_step_id:
            obj.tenant = obj.from_step.tenant
        super().save_model(request, obj, form, change)