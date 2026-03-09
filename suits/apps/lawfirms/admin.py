# apps/lawfirms/admin.py
#
# KEY CONCEPTS:
# - TenantAdminMixin: makes all dropdowns (law_firm, client, workflow_template, etc.)
#   show real data by bypassing the TenantManager filter in admin.
# - attach_workflow_view: custom admin page to attach a workflow template to selected cases.
#   It renders templates/admin/lawfirms/attach_workflow.html.
# - advance_step_action: moves selected cases to their next workflow step.

from django.contrib import admin, messages
from django.shortcuts import render, redirect
from django.urls import path
from django.http import HttpResponseRedirect

from apps.core.admin_mixins import TenantAdminMixin
from apps.workflows.engine import WorkflowEngine
from .models import LawFirm, Attorney, Client, Case, Document


# ─── LawFirm ────────────────────────────────────────────────────────────────

@admin.register(LawFirm)
class LawFirmAdmin(TenantAdminMixin, admin.ModelAdmin):
    list_display  = ("name", "code", "tenant", "active")
    search_fields = ("name", "code")
    list_filter   = ("tenant", "active")


# ─── Attorney ───────────────────────────────────────────────────────────────

@admin.register(Attorney)
class AttorneyAdmin(TenantAdminMixin, admin.ModelAdmin):
    list_display  = ("user", "law_firm", "title", "active")
    search_fields = ("user__username", "law_firm__name")
    list_filter   = ("active",)


# ─── Client ─────────────────────────────────────────────────────────────────

@admin.register(Client)
class ClientAdmin(TenantAdminMixin, admin.ModelAdmin):
    list_display  = ("first_name", "last_name", "email", "law_firm")
    search_fields = ("first_name", "last_name", "email")
    list_filter   = ("law_firm__tenant",)


# ─── Document ───────────────────────────────────────────────────────────────

@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    # Document uses plain models.Model (no TenantManager), no mixin needed
    list_display  = ("filename", "case", "uploaded_at")
    search_fields = ("filename", "case__code")


# ─── Case ───────────────────────────────────────────────────────────────────

@admin.register(Case)
class CaseAdmin(TenantAdminMixin, admin.ModelAdmin):
    list_display  = ("code", "title", "law_firm", "client", "workflow_template", "current_step", "status", "start_date", "end_date")
    search_fields = ("code", "title", "law_firm__name", "client__first_name", "client__last_name")
    list_filter   = ("tenant", "status")
    actions       = ["attach_workflow_action", "advance_step_action"]

    # ── Custom URL for the intermediate attach-workflow page ─────────────────

    def get_urls(self):
        urls = super().get_urls()
        custom = [
            path(
                "attach-workflow/",
                self.admin_site.admin_view(self.attach_workflow_view),
                name="lawfirms_case_attach_workflow",
            ),
        ]
        # Custom URLs must come BEFORE default URLs so Django finds them first
        return custom + urls

    # ── Action: opens the intermediate page ─────────────────────────────────

    def attach_workflow_action(self, request, queryset):
        """
        Admin action that redirects to the attach_workflow_view
        passing the selected case IDs as query params.
        """
        selected_ids = queryset.values_list("id", flat=True)
        ids_str = ",".join(str(i) for i in selected_ids)
        return HttpResponseRedirect(f"attach-workflow/?ids={ids_str}")

    attach_workflow_action.short_description = "Attach workflow to selected cases"

    # ── Intermediate view: shows workflow picker form ────────────────────────

    def attach_workflow_view(self, request):
        """
        GET:  render a form listing all WorkflowTemplates the admin can pick.
        POST: assign the chosen workflow to each selected case and save.
        """
        from apps.workflows.models import WorkflowTemplate

        ids_str = request.GET.get("ids") or request.POST.get("ids", "")
        case_ids = [int(i) for i in ids_str.split(",") if i.strip().isdigit()]

        # Use unscoped to show all cases regardless of tenant context
        cases = Case.unscoped.filter(id__in=case_ids)

        # Use unscoped so all templates appear in the dropdown
        templates = WorkflowTemplate.unscoped.filter(active=True).order_by("tenant__name", "name")

        if request.method == "POST":
            template_id = request.POST.get("workflow_template_id")
            if not template_id:
                messages.error(request, "Please select a workflow template.")
            else:
                try:
                    template = WorkflowTemplate.unscoped.get(id=template_id)
                    first_step = template.steps.order_by("order").first()

                    updated = 0
                    for case in cases:
                        case.workflow_template = template
                        # Immediately put the case on the first step
                        if first_step:
                            case.current_step = first_step
                            case.status = first_step.name
                        # Skip full_clean() in admin to avoid cross-tenant validation noise
                        case.save_base(update_fields=["workflow_template", "current_step", "status"])
                        updated += 1

                    messages.success(request, f"Workflow '{template.name}' attached to {updated} case(s).")
                    return redirect("..")
                except WorkflowTemplate.DoesNotExist:
                    messages.error(request, "Selected workflow template not found.")

        context = {
            **self.admin_site.each_context(request),
            "title": "Attach Workflow to Cases",
            "cases": cases,
            "templates": templates,
            "ids": ids_str,
        }
        # This template lives at: suits/templates/admin/lawfirms/attach_workflow.html
        return render(request, "admin/lawfirms/attach_workflow.html", context)

    # ── Action: advance step ─────────────────────────────────────────────────

    def advance_step_action(self, request, queryset):
        """
        Move each selected case to its next workflow step.
        Uses WorkflowEngine which evaluates transitions and branching rules.
        """
        success = 0
        errors  = []

        for case in queryset:
            try:
                WorkflowEngine.advance(case, context={})
                success += 1
            except Exception as e:
                errors.append(f"Case {case.code}: {e}")

        if success:
            messages.success(request, f"Advanced {success} case(s) to next step.")
        for err in errors:
            messages.error(request, err)

    advance_step_action.short_description = "Advance selected cases to next workflow step"