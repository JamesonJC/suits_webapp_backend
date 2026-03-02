from rest_framework import serializers
from .models import WorkflowTemplate

class WorkflowTemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = WorkflowTemplate
        fields = "__all__"