# apps/workflows/serializers.py

from rest_framework import serializers
from .models import WorkflowTemplate, WorkflowStep, WorkflowTransition


class WorkflowTransitionSerializer(serializers.ModelSerializer):
    """
    Serialises a branching transition between two steps.
    `to_step_name` is a bonus read-only field so the frontend doesn't need
    a second lookup to display the destination step's name.
    """
    to_step_name = serializers.CharField(source="to_step.name", read_only=True)

    class Meta:
        model  = WorkflowTransition
        fields = [
            "id",
            "from_step",
            "to_step",
            "to_step_name",
            "label",
            "condition_field",
            "condition_value",
            "priority",
        ]
        read_only_fields = ("tenant",)


class WorkflowStepSerializer(serializers.ModelSerializer):
    """
    Serialises a single step, including all its outgoing transitions.
    The frontend can use outgoing_transitions to render a button per outcome
    (e.g. "Approve", "Reject") without a second API call.
    """
    outgoing_transitions = WorkflowTransitionSerializer(many=True, read_only=True)

    class Meta:
        model  = WorkflowStep
        fields = [
            "id",
            "workflow",
            "name",
            "description",
            "order",
            "requires_attachment",
            "outgoing_transitions",
        ]
        read_only_fields = ("workflow",)


class WorkflowTemplateSerializer(serializers.ModelSerializer):
    """
    Full template with every step and each step's transitions.
    One GET gives the frontend everything needed to render the full workflow graph.
    """
    steps = WorkflowStepSerializer(many=True, read_only=True)

    class Meta:
        model  = WorkflowTemplate
        fields = ["id", "name", "description", "active", "steps"]
        read_only_fields = ("tenant",)