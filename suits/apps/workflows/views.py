# apps/workflows/views.py

from rest_framework import viewsets
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated

from apps.tenants.models import Tenant
from .models import WorkflowTemplate, WorkflowStep, WorkflowTransition
from .serializers import (
    WorkflowTemplateSerializer,
    WorkflowStepSerializer,
    WorkflowTransitionSerializer,
)


def _tenant_from_request(request):
    """
    Reads X-Tenant-Code header and returns the matching active Tenant, or None.
    Centralised so all views use identical logic.
    """
    code = request.META.get("HTTP_X_TENANT_CODE")
    if not code:
        return None
    try:
        return Tenant.objects.get(code=code, active=True)
    except Tenant.DoesNotExist:
        return None


class WorkflowTemplateViewSet(viewsets.ModelViewSet):
    """
    CRUD for WorkflowTemplates, always scoped to the requesting tenant.
    Endpoint: /api/workflow-templates/
    """
    serializer_class   = WorkflowTemplateSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        tenant = _tenant_from_request(self.request)
        if not tenant:
            return WorkflowTemplate.objects.none()
        return WorkflowTemplate.objects.filter(tenant=tenant)

    def perform_create(self, serializer):
        tenant = _tenant_from_request(self.request)
        if not tenant:
            raise PermissionDenied("Valid X-Tenant-Code header required.")
        serializer.save(tenant=tenant)


class WorkflowStepViewSet(viewsets.ModelViewSet):
    """
    CRUD for WorkflowSteps, scoped to the requesting tenant's workflows.
    Endpoint: /api/steps/
    """
    serializer_class   = WorkflowStepSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        tenant = _tenant_from_request(self.request)
        if not tenant:
            return WorkflowStep.objects.none()
        return WorkflowStep.objects.filter(workflow__tenant=tenant)

    def perform_create(self, serializer):
        tenant = _tenant_from_request(self.request)
        if not tenant:
            raise PermissionDenied("Valid X-Tenant-Code header required.")

        workflow = serializer.validated_data.get("workflow")
        if workflow.tenant != tenant:
            raise PermissionDenied("Cannot add a step to another tenant's workflow.")

        serializer.save()


class WorkflowTransitionViewSet(viewsets.ModelViewSet):
    """
    CRUD for WorkflowTransitions (the branching rules between steps).
    Endpoint: /api/transitions/

    Example POST to create a conditional branch:
    {
        "from_step": 3,
        "to_step": 5,
        "label": "Approved",
        "condition_field": "decision",
        "condition_value": "APPROVED",
        "priority": 1
    }

    Leave condition_field and condition_value blank for a default/fallback path.
    """
    serializer_class   = WorkflowTransitionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        tenant = _tenant_from_request(self.request)
        if not tenant:
            return WorkflowTransition.objects.none()
        return WorkflowTransition.objects.filter(
            from_step__workflow__tenant=tenant
        )

    def perform_create(self, serializer):
        tenant = _tenant_from_request(self.request)
        if not tenant:
            raise PermissionDenied("Valid X-Tenant-Code header required.")

        from_step = serializer.validated_data.get("from_step")
        to_step   = serializer.validated_data.get("to_step")

        if from_step.workflow != to_step.workflow:
            raise PermissionDenied("Both steps must belong to the same workflow.")
        if from_step.workflow.tenant != tenant:
            raise PermissionDenied("Cannot create transitions for another tenant's workflow.")

        serializer.save(tenant=tenant)