from rest_framework import serializers
from .models import WorkflowTemplate, WorkflowStep


class WorkflowStepSerializer(serializers.ModelSerializer):
    class Meta:
        model = WorkflowStep
        fields = "__all__"
        read_only_fields = ("workflow",)


class WorkflowTemplateSerializer(serializers.ModelSerializer):
    steps = WorkflowStepSerializer(many=True, read_only=True)

    class Meta:
        model = WorkflowTemplate
        fields = "__all__"
        read_only_fields = ("tenant",)