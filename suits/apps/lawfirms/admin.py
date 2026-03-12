# apps/lawfirms/admin.py
#
# ADMIN PHILOSOPHY FOR THIS PROJECT:
# ─────────────────────────────────
# Admin is for DATA MANAGEMENT only:
#   - Creating/editing law firms, clients, cases, attorneys
#   - Attaching workflow templates to cases
#   - Viewing case status and current step (read-only)
#
# WORKFLOW PROGRESSION (advancing steps / choosing transitions) is handled
# entirely by the React frontend via the API:
#   POST /api/cases/{id}/advance_step/   body: { "transition_id": N }
#   GET  /api/cases/{id}/workflow_status/ returns available transitions
#
# The only exception in admin is single-transition (linear) steps — those
# can be auto-advanced because there is no decision to make.
# Multi-transition (branching) steps show a clear info message pointing
# the admin to the frontend.

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
    list_display  = ("filename", "case", "uploaded_at")
    search_fields = ("filename", "case__code")


# ─── Case ───────────────────────────────────────────────────────────────────

@admin.register(Case)
class CaseAdmin(TenantAdminMixin, admin.ModelAdmin):
    list_display    = ("code", "title", "law_firm", "client", "workflow_template",
                       "current_step", "status", "start_date", "end_date")
    search_fields   = ("code", "title", "law_firm__name",
                       "client__first_name", "client__last_name")
    list_filter     = ("tenant", "status")

    # ✅ current_step and status are ALWAYS managed by WorkflowEngine.
    # Never allow manual editing — it would bypass validation and audit logs.
    readonly_fields = ("current_step", "status")

    actions = ["attach_workflow_action", "advance_step_action"]

    # ── Custom URL: Attach Workflow ──────────────────────────────────────────

    def get_urls(self):
        urls = super().get_urls()
        custom = [
            path(
                "attach-workflow/",
                self.admin_site.admin_view(self.attach_workflow_view),
                name="lawfirms_case_attach_workflow",
            ),
        ]
        return custom + urls

    def attach_workflow_action(self, request, queryset):
        """Redirect to the attach-workflow picker page with selected case IDs."""
        ids_str = ",".join(str(i) for i in queryset.values_list("id", flat=True))
        return HttpResponseRedirect(f"attach-workflow/?ids={ids_str}")

    attach_workflow_action.short_description = "Attach workflow to selected cases"

    def attach_workflow_view(self, request):
        """
        GET:  render a form listing all active WorkflowTemplates.
        POST: assign the chosen workflow to each selected case.
        """
        from apps.workflows.models import WorkflowTemplate

        ids_str   = request.GET.get("ids") or request.POST.get("ids", "")
        case_ids  = [int(i) for i in ids_str.split(",") if i.strip().isdigit()]
        cases     = Case.unscoped.filter(id__in=case_ids)
        templates = WorkflowTemplate.unscoped.filter(active=True).order_by("tenant__name", "name")

        if request.method == "POST":
            template_id = request.POST.get("workflow_template_id")
            if not template_id:
                messages.error(request, "Please select a workflow template.")
            else:
                try:
                    template   = WorkflowTemplate.unscoped.get(id=template_id)
                    first_step = template.steps.order_by("order").first()
                    updated    = 0
                    for case in cases:
                        case.workflow_template = template
                        if first_step:
                            case.current_step = first_step
                            case.status       = first_step.name
                        case.save_base(update_fields=["workflow_template", "current_step", "status"])
                        updated += 1
                    messages.success(request, f"Workflow '{template.name}' attached to {updated} case(s).")
                    return redirect("..")
                except WorkflowTemplate.DoesNotExist:
                    messages.error(request, "Selected workflow template not found.")

        context = {
            **self.admin_site.each_context(request),
            "title":     "Attach Workflow to Cases",
            "cases":     cases,
            "templates": templates,
            "ids":       ids_str,
        }
        return render(request, "admin/lawfirms/attach_workflow.html", context)

    # ── Action: Advance Step ─────────────────────────────────────────────────

    def advance_step_action(self, request, queryset):
        """
        Admin action for advancing cases through their workflow.

        BEHAVIOUR:
        ─────────
        • No workflow attached      → warning, skip.
        • No transitions defined    → warning, skip.
        • Exactly ONE transition    → auto-advance. No human input needed.
        • MORE THAN ONE transition  → info message listing the options.
                                      The attorney must use the React frontend
                                      to choose which path to take.
                                      Admin intentionally does NOT handle this
                                      to keep the decision-making in the proper UI.
        """
        from apps.workflows.models import WorkflowTransition

        for case in queryset:

            # ── Guard: no workflow attached ──────────────────────────────────
            if not case.workflow_template:
                messages.warning(
                    request,
                    f"'{case.code}': no workflow attached — skipped."
                )
                continue

            # ── Guard: no current step ───────────────────────────────────────
            if not case.current_step:
                messages.warning(
                    request,
                    f"'{case.code}': has a workflow but no current step — skipped."
                )
                continue

            transitions = list(
                WorkflowTransition.unscoped
                .filter(from_step=case.current_step)
                .select_related("to_step")
                .order_by("label")
            )

            # ── No transitions defined ───────────────────────────────────────
            if len(transitions) == 0:
                messages.warning(
                    request,
                    f"'{case.code}': no transitions defined from "
                    f"step '{case.current_step.name}'. "
                    f"Add transitions in Workflow Transitions admin."
                )

            # ── Single transition: auto-advance ──────────────────────────────
            elif len(transitions) == 1:
                try:
                    WorkflowEngine.advance(case, transition_id=transitions[0].id)
                    messages.success(
                        request,
                        f"'{case.code}': advanced to '{transitions[0].to_step.name}'."
                    )
                except Exception as e:
                    messages.error(request, f"'{case.code}': {e}")

            # ── Multiple transitions: defer to frontend ───────────────────────
            else:
                # Build a human-readable list of the available options
                # so the admin knows exactly what choices exist in the frontend
                options = " | ".join(
                    f"{t.label} → {t.to_step.name}"
                    for t in transitions
                )
                messages.info(
                    request,
                    f"'{case.code}' is at a branching step "
                    f"('{case.current_step.name}') with multiple options: "
                    f"{options}. "
                    f"Open this case in the app to choose the next step."
                )

    advance_step_action.short_description = "Advance selected cases to next step"