from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from apps.rbac.permissions import HasPlatformPermission
from .models import WorkflowTemplate
from .serializers import WorkflowTemplateSerializer


class WorkflowTemplateViewSet(viewsets.ModelViewSet):
    queryset = WorkflowTemplate.objects.all()
    serializer_class = WorkflowTemplateSerializer

    permission_classes = [IsAuthenticated, HasPlatformPermission]
    required_permission = "workflow.create"