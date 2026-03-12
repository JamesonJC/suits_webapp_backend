# apps/workflows/services.py
#
# CaseWorkflowService is used by API views.
# It wraps WorkflowEngine and provides helper methods for the frontend.

from .models import WorkflowTemplate, WorkflowStep, WorkflowTransition
from .engine import WorkflowEngine


class CaseWorkflowService:

    @staticmethod
    def attach_workflow(case, workflow_template):
        """
        Assign a workflow to a case and place it on step 1.

        This is called:
          - When a case is created with a workflow_template selected
          - When POST /api/cases/{id}/attach_workflow/ is called

        Raises:
            ValueError: template is from a different tenant, or has no steps.
        """
        if workflow_template.tenant != case.law_firm.tenant:
            raise ValueError("Cannot attach a workflow from a different tenant.")

        has_steps = WorkflowStep.unscoped.filter(workflow=workflow_template).exists()
        if not has_steps:
            raise ValueError(
                f"Workflow '{workflow_template.name}' has no steps. "
                "Add steps before attaching to a case."
            )

        case.workflow_template = workflow_template
        case.current_step      = None  # Reset so Case.save() places on step 1
        case.save()
        return case

    @staticmethod
    def advance_step(case, transition_id: int):
        """
        Move the case forward using the transition the attorney chose.

        Args:
            case:          The Case instance.
            transition_id: ID of the WorkflowTransition chosen by the attorney.

        Raises:
            ValueError: wrapping any engine error with a clean message.
        """
        try:
            return WorkflowEngine.advance(case, transition_id=transition_id)
        except Exception as e:
            raise ValueError(str(e))

    @staticmethod
    def get_available_transitions(case):
        """
        Return all transitions the attorney can choose from the current step.

        This is what the frontend renders as action buttons.

        Example response:
        [
          {"id": 3, "label": "Proceed to Negotiation",    "to_step_id": 4, "to_step_name": "Negotiation"},
          {"id": 4, "label": "Request More Documents",     "to_step_id": 2, "to_step_name": "Document Collection"},
          {"id": 5, "label": "Escalate to Partner Review", "to_step_id": 7, "to_step_name": "Partner Review"},
        ]

        The attorney sees these labels and picks the one matching the situation.
        The frontend then calls POST /advance_step/ with the chosen transition id.
        """
        if not case.current_step_id:
            return []

        transitions = (
            WorkflowTransition.unscoped
            .filter(from_step_id=case.current_step_id)
            .select_related("to_step")
            .order_by("label")
        )

        return [
            {
                "id":          t.id,
                "label":       t.label,
                "to_step_id":  t.to_step_id,
                "to_step_name": t.to_step.name,
                "to_step_description": t.to_step.description,
            }
            for t in transitions
        ]

    @staticmethod
    def get_all_steps(case):
        """
        Return every step in the workflow with an is_current flag.
        Used to render a progress/timeline bar in the frontend.
        """
        if not case.workflow_template_id:
            return []

        steps = (
            WorkflowStep.unscoped
            .filter(workflow_id=case.workflow_template_id)
            .order_by("order")
        )

        return [
            {
                "id":          s.id,
                "name":        s.name,
                "description": s.description,
                "order":       s.order,
                "is_current":  s.id == case.current_step_id,
            }
            for s in steps
        ]