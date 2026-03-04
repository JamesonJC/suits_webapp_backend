from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import PermissionDenied
from apps.tenants.models import Tenant
from .models import WorkflowTemplate, WorkflowStep
from .serializers import WorkflowTemplateSerializer, WorkflowStepSerializer


class TenantScopedMixin:
    """
    Extract tenant directly from request.META.
    This works 100% with DRF test client.
    """

    def get_tenant(self):
        tenant_code = self.request.META.get("HTTP_X_TENANT_CODE")
        if not tenant_code:
            return None
        try:
            return Tenant.objects.get(code=tenant_code, active=True)
        except Tenant.DoesNotExist:
            return None


class WorkflowTemplateViewSet(viewsets.ModelViewSet):
    serializer_class = WorkflowTemplateSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        tenant_code = self.request.META.get("HTTP_X_TENANT_CODE")
        if not tenant_code:
            return WorkflowTemplate.objects.none()

        try:
            tenant = Tenant.objects.get(code=tenant_code, active=True)
        except Tenant.DoesNotExist:
            return WorkflowTemplate.objects.none()

        # Only workflows for this tenant
        return WorkflowTemplate.objects.filter(tenant=tenant)

    def perform_create(self, serializer):
        tenant_code = self.request.META.get("HTTP_X_TENANT_CODE")
        try:
            tenant = Tenant.objects.get(code=tenant_code, active=True)
        except Tenant.DoesNotExist:
            raise PermissionDenied("Tenant not found")

        serializer.save(tenant=tenant)


class WorkflowStepViewSet(viewsets.ModelViewSet):
    serializer_class = WorkflowStepSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        tenant_code = self.request.META.get("HTTP_X_TENANT_CODE")
        if not tenant_code:
            return WorkflowStep.objects.none()

        try:
            tenant = Tenant.objects.get(code=tenant_code, active=True)
        except Tenant.DoesNotExist:
            return WorkflowStep.objects.none()

        # Only steps for workflows belonging to this tenant
        return WorkflowStep.objects.filter(workflow__tenant=tenant)

    def perform_create(self, serializer):
        tenant_code = self.request.META.get("HTTP_X_TENANT_CODE")
        try:
            tenant = Tenant.objects.get(code=tenant_code, active=True)
        except Tenant.DoesNotExist:
            raise PermissionDenied("Tenant not found")

        workflow = serializer.validated_data.get("workflow")
        if workflow.tenant != tenant:
            raise PermissionDenied("Cannot add step to another tenant")

        serializer.save()