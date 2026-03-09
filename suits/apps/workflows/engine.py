# apps/workflows/engine.py
#
# WorkflowEngine: handles moving a Case from one step to the next.
#
# HOW BRANCHING WORKS:
# Each WorkflowStep can have multiple outgoing WorkflowTransitions.
# A transition has optional condition_field + condition_value.
# When advancing, you pass a `context` dict (e.g. {"decision": "APPROVED"}).
# The engine evaluates transitions in priority order and takes the first match.
# If condition_field is blank, the transition always matches (default path).
#
# EXAMPLE:
#   Step "Review" has two transitions:
#     1. condition_field="decision", condition_value="APPROVED" → step "Finalise"
#     2. condition_field="decision", condition_value="REJECTED" → step "Revise"
#   Calling advance(case, context={"decision": "APPROVED"}) goes to "Finalise".

from django.db import transaction
from apps.audit.services import log_action


class WorkflowEngine:

    @staticmethod
    @transaction.atomic
    def advance(case, context: dict = None):
        """
        Move `case` to its next workflow step based on transitions and context.

        Args:
            case:    A Case instance (must have workflow_template and current_step set).
            context: Dict of field→value pairs used to evaluate branching conditions.
                     Example: {"decision": "APPROVED"}

        Returns:
            The updated Case instance.

        Raises:
            Exception if no workflow is attached, or no matching transition found.
        """
        if context is None:
            context = {}

        # Lock the case row so concurrent requests don't double-advance
        from apps.lawfirms.models import Case as CaseModel
        case = CaseModel.unscoped.select_for_update().get(id=case.id)

        if not case.workflow_template:
            raise Exception(
                f"Case '{case.code}' has no workflow attached. "
                "Use 'Attach workflow' action first."
            )

        previous_step_name = case.current_step.name if case.current_step else None

        # ── Find the next step ──────────────────────────────────────────────

        if case.current_step is None:
            # Case hasn't started yet — go to the very first step
            next_step = (
                case.workflow_template.steps
                .order_by("order")
                .first()
            )
            if not next_step:
                raise Exception(
                    f"Workflow '{case.workflow_template.name}' has no steps defined."
                )
        else:
            # Evaluate outgoing transitions from the current step in priority order
            transitions = case.current_step.outgoing_transitions.order_by("priority")

            if not transitions.exists():
                raise Exception(
                    f"No transitions defined from step '{case.current_step.name}'. "
                    "Add a WorkflowTransition in admin to continue."
                )

            next_step = None
            for transition in transitions:
                if transition.matches(context):
                    next_step = transition.to_step
                    break

            if not next_step:
                raise Exception(
                    f"No valid next step found from '{case.current_step.name}' "
                    f"with context {context}. "
                    "Check that transitions are configured correctly."
                )

        # ── Validate any gate conditions ────────────────────────────────────

        if next_step.requires_attachment:
            if not case.attachments.exists():  # type: ignore[attr-defined]
                raise Exception(
                    f"Step '{next_step.name}' requires an attachment. "
                    "Upload a file before advancing."
                )

        # ── Apply the transition ────────────────────────────────────────────

        case.current_step = next_step
        case.status = next_step.name
        # Save only these two fields to avoid triggering full_clean cross-tenant checks
        case.save_base(update_fields=["current_step", "status"])

        # ── Audit log ───────────────────────────────────────────────────────

        try:
            log_action(
                action="TRANSITION",
                instance=case,
                before={"step": previous_step_name},
                after={"step": next_step.name},
            )
        except Exception:
            # Never let audit failure block the actual transition
            pass

        return case