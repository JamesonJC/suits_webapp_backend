# apps/workflows/services.py
#
# CaseWorkflowService is the single entry point for all workflow operations
# on a Case. Views, admin actions, and API endpoints all call this — never
# touch Case.current_step or Case.status directly.
#
# FLOW
# ────
# 1. Attorney picks a workflow template and calls attach_workflow()
#    → case.workflow_template is set, case.current_step moves to step 1
#    → case.status becomes the name of step 1
#
# 2. Attorney reviews the case, makes a decision, calls advance_step()
#    → engine evaluates transitions against the provided context
#    → case.current_step moves to the next step
#    → case.status updates automatically (Case.save() does this)
#
# 3. Frontend calls get_available_transitions() to know what buttons to show
#    e.g. ["Approve", "Reject", "Request More Info"]

from django.db import transaction
from apps.audit.services import log_action
from .models import WorkflowTemplate, WorkflowStep, WorkflowTransition


class CaseWorkflowService:

    @staticmethod
    @transaction.atomic
    def attach_workflow(case, workflow_template):
        """
        Attach a WorkflowTemplate to a Case and immediately move it to step 1.

        Args:
            case:              A Case instance (already saved).
            workflow_template: The WorkflowTemplate to attach.

        Raises:
            ValueError: If the template belongs to a different tenant than the case,
                        or if the template has no steps defined.
        """
        # Guard: template must belong to the same tenant as the case
        if workflow_template.tenant != case.law_firm.tenant:
            raise ValueError(
                "Cannot attach a workflow from a different tenant."
            )

        first_step = (
            WorkflowStep.objects
            .filter(workflow=workflow_template)
            .order_by("order")
            .first()
        )

        if not first_step:
            raise ValueError(
                f"Workflow '{workflow_template.name}' has no steps defined. "
                "Add steps before attaching it to a case."
            )

        previous_status = case.status

        case.workflow_template = workflow_template
        case.current_step      = first_step
        # Case.save() will set case.status = first_step.name automatically
        case.save()

        log_action(
            action="UPDATE",
            instance=case,
            before={"status": previous_status, "workflow": None},
            after={
                "status":   case.status,
                "workflow": workflow_template.name,
                "step":     first_step.name,
            },
        )

        return case

    @staticmethod
    @transaction.atomic
    def advance_step(case, context=None):
        """
        Move a Case to the next workflow step.

        Args:
            case:    A Case instance that has a workflow_template attached.
            context: Dict of field values used to evaluate branching conditions.
                     e.g. {"decision": "APPROVED"}
                     If omitted, only unconditional (default) transitions fire.

        Returns:
            The updated Case instance.

        Raises:
            ValueError: If no workflow is attached, or no valid next step exists.
        """
        if context is None:
            context = {}

        if not case.workflow_template:
            raise ValueError(
                "This case has no workflow attached. "
                "Use attach_workflow() first."
            )

        previous_step_name = case.current_step.name if case.current_step else None

        next_step = CaseWorkflowService._resolve_next_step(case, context)

        if not next_step:
            raise ValueError(
                f"No valid next step found from '{previous_step_name}' "
                f"with context {context}. "
                "Check that transitions are configured correctly."
            )

        # Validate before moving (e.g. attachment required)
        CaseWorkflowService._validate(case, next_step)

        case.current_step = next_step
        # Case.save() auto-sets case.status = next_step.name
        case.save()

        log_action(
            action="TRANSITION",
            instance=case,
            before={"step": previous_step_name},
            after={"step": next_step.name, "context": context},
        )

        return case

    @staticmethod
    def get_available_transitions(case):
        """
        Returns a list of possible next moves from the case's current step.

        Used by the frontend to render action buttons, and by the admin to
        show the "Advance Step" dropdown.

        Returns:
            List of dicts, e.g.:
            [
                {"label": "Approve",  "condition_field": "decision", "condition_value": "APPROVED", "to_step_name": "Processing"},
                {"label": "Reject",   "condition_field": "decision", "condition_value": "REJECTED", "to_step_name": "Rejection Review"},
                {"label": "Continue", "condition_field": None,       "condition_value": None,       "to_step_name": "Final Review"},
            ]
            Empty list if no transitions defined (linear workflow) or no current step.
        """
        if not case.current_step:
            return []

        transitions = (
            WorkflowTransition.objects
            .filter(from_step=case.current_step)
            .select_related("to_step")
            .order_by("priority")
        )

        return [
            {
                "label":           t.label,
                "condition_field": t.condition_field,
                "condition_value": t.condition_value,
                "to_step_id":      t.to_step_id,
                "to_step_name":    t.to_step.name,
            }
            for t in transitions
        ]

    @staticmethod
    def get_all_steps(case):
        """
        Returns all steps in this case's workflow with a flag showing
        which one is current. Useful for rendering a progress bar in the UI.
        """
        if not case.workflow_template:
            return []

        steps = (
            WorkflowStep.objects
            .filter(workflow=case.workflow_template)
            .order_by("order")
        )

        return [
            {
                "id":       step.id,
                "name":     step.name,
                "order":    step.order,
                "is_current": (case.current_step_id == step.id),
            }
            for step in steps
        ]

    # ── Internal helpers ──────────────────────────────────────────────────────

    @staticmethod
    def _resolve_next_step(case, context):
        """
        Determines the next step using transitions (branching) or
        linear order fallback (no transitions defined).
        """
        if case.current_step:
            transitions = (
                WorkflowTransition.objects
                .filter(from_step=case.current_step)
                .select_related("to_step")
                .order_by("priority")
            )

            if transitions.exists():
                # Try conditional transitions first
                for t in transitions:
                    if t.condition_field and t.condition_value:
                        if str(context.get(t.condition_field, "")) == str(t.condition_value):
                            return t.to_step

                # Fall back to first unconditional (default) transition
                for t in transitions:
                    if not t.condition_field:
                        return t.to_step

                return None  # transitions exist but nothing matched

        # Linear fallback: find the step with the next order number
        steps = (
            WorkflowStep.objects
            .filter(workflow=case.workflow_template)
            .order_by("order")
        )

        if not case.current_step:
            return steps.first()

        return steps.filter(order__gt=case.current_step.order).first()

    @staticmethod
    def _validate(case, next_step):
        """Pre-move checks. Raises ValueError if requirements aren't met."""
        if next_step.requires_attachment:
            # Check via the case's related documents
            if not Document.objects.filter(case=case).exists():
                raise ValueError(
                    f"Step '{next_step.name}' requires an attachment. "
                    "Please upload a document before advancing."
                )