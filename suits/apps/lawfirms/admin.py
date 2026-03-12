# apps/lawfirms/admin.py
#
# The Case admin lets you:
#   - Create a case and assign a workflow_template directly on the form.
#     Saving auto-places the case on step 1.
#   - Select cases and use the "Advance step" action to move them forward.
#     In admin, since we can't show a dropdown per case in a bulk action,
#     the advance action takes the first available transition for each case.
#     For branching decisions, attorneys use the API: POST /advance_step/
#     with the transition_id they choose.

from django.contrib import admin, messages
from apps.core.admin_mixins import TenantAdminMixin
from apps.workflows.engine import WorkflowEngine
from apps.workflows.models import WorkflowTransition
from .models import LawFirm, Attorney, Client, Case, Document


@admin.register(LawFirm)
class LawFirmAdmin(TenantAdminMixin, admin.ModelAdmin):
    list_display  = ("name", "code", "tenant", "active")
    search_fields = ("name", "code")
    list_filter   = ("tenant", "active")


@admin.register(Attorney)
class AttorneyAdmin(TenantAdminMixin, admin.ModelAdmin):
    list_display  = ("user", "law_firm", "title", "active")
    search_fields = ("user__username", "law_firm__name")
    list_filter   = ("law_firm__tenant", "active")


@admin.register(Client)
class ClientAdmin(TenantAdminMixin, admin.ModelAdmin):
    list_display  = ("first_name", "last_name", "email", "law_firm")
    search_fields = ("first_name", "last_name", "email")
    list_filter   = ("law_firm__tenant",)


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display  = ("filename", "case", "uploaded_at")
    search_fields = ("filename", "case__code")


@admin.register(Case)
class CaseAdmin(TenantAdminMixin, admin.ModelAdmin):
    list_display = (
        "code", "title", "law_firm", "client",
        "workflow_template", "current_step", "status", "start_date",
    )
    search_fields = ("code", "title", "law_firm__name", "client__first_name")
    list_filter   = ("tenant", "status", "workflow_template")

    # current_step and status are read-only — they're set by the engine
    readonly_fields = ("current_step", "status")

    fieldsets = (
        ("Case Details", {
            "fields": ("tenant", "law_firm", "client", "code", "title", "end_date"),
        }),
        ("Workflow", {
            "fields": ("workflow_template", "current_step", "status"),
            "description": (
                "Assign a workflow and save — the case will automatically start "
                "on step 1. Use the 'Advance step' action to progress cases forward."
            ),
        }),
    )

    actions = ["advance_step_action"]

    def advance_step_action(self, request, queryset):
        """
        Admin action: advance selected cases using their first available transition.

        For cases with only one transition from their current step, this works perfectly.
        For cases with multiple options (branching), attorneys should use the API:
          POST /api/cases/{id}/advance_step/   Body: {"transition_id": X}
        """
        success = 0
        errors  = []

        for case in queryset:
            if not case.workflow_template_id:
                errors.append(f"'{case.code}': No workflow assigned.")
                continue

            if not case.current_step_id:
                errors.append(f"'{case.code}': Not yet started on any step.")
                continue

            # Get available transitions from current step
            transitions = (
                WorkflowTransition.unscoped
                .filter(from_step_id=case.current_step_id)
                .order_by("label")
            )

            if not transitions.exists():
                errors.append(
                    f"'{case.code}': No transitions from '{case.current_step.name}'. "
                    "Add transitions in Admin → Workflow Transitions."
                )
                continue

            if transitions.count() > 1:
                # Multiple options — list them so the admin knows to use the API
                options = ", ".join(f'"{t.label}"' for t in transitions)
                errors.append(
                    f"'{case.code}': Multiple options available: {options}. "
                    "Use the API (POST /advance_step/ with transition_id) to choose."
                )
                continue

            # Single transition — safe to apply automatically
            try:
                WorkflowEngine.advance(case, transition_id=transitions.first().id)
                success += 1
            except Exception as e:
                errors.append(f"'{case.code}': {e}")

        if success:
            self.message_user(request, f"Advanced {success} case(s).", messages.SUCCESS)
        for err in errors:
            self.message_user(request, err, messages.ERROR)

    advance_step_action.short_description = "Advance selected cases to next step"