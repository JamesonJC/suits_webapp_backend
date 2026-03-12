# apps/workflows/engine.py
#
# WorkflowEngine: applies attorney-chosen transitions to a case.
#
# The attorney sees available options and picks one by transition_id.
# The engine validates the choice and applies it. No automated decision-making.
#
# ALL queries use .unscoped (not .objects) because this engine is called
# from admin actions and API views alike — admin has no tenant header so
# TenantManager would return empty querysets.

from django.db import transaction
from apps.audit.services import log_action


class WorkflowEngine:

    @staticmethod
    @transaction.atomic
    def advance(case, transition_id: int):
        """
        Move `case` to the next step by applying a specific transition
        chosen by the attorney.

        Args:
            case:          A Case instance with a workflow attached.
            transition_id: The ID of the WorkflowTransition the attorney chose.
                           Get available options first via get_available_transitions().

        Returns:
            Updated Case instance.

        Raises:
            Exception with a clear message on any invalid state.
        """
        from apps.lawfirms.models import Case as CaseModel
        from apps.workflows.models import WorkflowTransition

        # Lock the row — prevents two concurrent requests from double-advancing
        case = CaseModel.unscoped.select_for_update().get(id=case.id)

        if not case.workflow_template_id:
            raise Exception(
                f"Case '{case.code}' has no workflow attached. "
                "Assign a workflow_template to this case first."
            )

        # Validate: the chosen transition must start from the case's current step
        try:
            transition = WorkflowTransition.unscoped.select_related("to_step").get(
                id=transition_id
            )
        except WorkflowTransition.DoesNotExist:
            raise Exception(f"Transition ID {transition_id} does not exist.")

        if transition.from_step_id != case.current_step_id:
            raise Exception(
                f"Transition '{transition.label}' starts from "
                f"'{transition.from_step.name}', but this case is currently on "
                f"'{case.current_step.name if case.current_step else 'no step'}'. "
                "Only transitions from the current step are valid."
            )

        next_step = transition.to_step

        # Gate: check if the destination step requires an attachment
        if next_step.requires_attachment:
            if not case.documents.exists():
                raise Exception(
                    f"Step '{next_step.name}' requires an uploaded document. "
                    "Upload a file to this case before advancing."
                )

        previous_step_name = case.current_step.name if case.current_step else None

        # Apply the transition
        case.current_step = next_step
        case.status       = next_step.name
        case.save_base(update_fields=["current_step", "status", "updated_at"])

        # Audit log (non-blocking — never let this break the transition)
        try:
            log_action(
                action="TRANSITION",
                instance=case,
                before={"step": previous_step_name},
                after={"step": next_step.name, "transition": transition.label},
            )
        except Exception:
            pass

        return case

    @staticmethod
    @transaction.atomic
    def start(case):
        """
        Place a case on step 1 of its workflow.
        Called automatically by Case.save() when workflow_template is first set.
        Can also be called manually to reset a case to the beginning.

        Args:
            case: A Case instance with workflow_template set.

        Returns:
            Updated Case instance.
        """
        from apps.lawfirms.models import Case as CaseModel
        from apps.workflows.models import WorkflowStep

        case = CaseModel.unscoped.select_for_update().get(id=case.id)

        if not case.workflow_template_id:
            raise Exception("Cannot start: no workflow_template set on this case.")

        first_step = (
            WorkflowStep.unscoped
            .filter(workflow_id=case.workflow_template_id)
            .order_by("order")
            .first()
        )

        if not first_step:
            raise Exception(
                f"Workflow '{case.workflow_template.name}' has no steps. "
                "Add steps in Admin → Workflow Templates (steps are inline)."
            )

        previous = case.current_step.name if case.current_step else None

        case.current_step = first_step
        case.status       = first_step.name
        case.save_base(update_fields=["current_step", "status", "updated_at"])

        try:
            log_action(
                action="TRANSITION",
                instance=case,
                before={"step": previous},
                after={"step": first_step.name, "transition": "Workflow started"},
            )
        except Exception:
            pass

        return case