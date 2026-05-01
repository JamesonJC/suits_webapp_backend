# apps/lawfirms/views.py
#
# HOW THE WORKFLOW API WORKS:
#
# 1. Create a case (workflow_template can be set on creation):
#    POST /api/cases/
#    Body: {"code": "PI-001", "title": "...", "client": 3, "workflow_template": 2}
#    → Case created, auto-placed on step 1 of the workflow.
#
# 2. See where the case is and what moves are available:
#    GET /api/cases/{id}/workflow_status/
#    Response:
#      {
#        "workflow": "Personal Injury",
#        "current_step": "Initial Consultation",
#        "steps": [...all steps with is_current flag...],
#        "available_transitions": [
#          {"id": 3, "label": "Proceed to Document Collection", "to_step_name": "..."},
#          {"id": 4, "label": "Close Case - No Merit",          "to_step_name": "Closed"},
#        ]
#      }
#
# 3. Attorney picks one and advances:
#    POST /api/cases/{id}/advance_step/
#    Body: {"transition_id": 3}
#    → Case moves to "Document Collection". No context dicts. No auto-rules.
#    → Attorney chose. System applied.
#
# 4. Attach or change workflow:
#    POST /api/cases/{id}/attach_workflow/
#    Body: {"workflow_template_id": 5}

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.workflows.services import CaseWorkflowService
from apps.workflows.models import WorkflowTemplate
from .models import LawFirm, Attorney, Client, Case, Document
from .serializers import (
    LawFirmSerializer,
    AttorneySerializer,
    ClientSerializer,
    CaseSerializer,
    DocumentSerializer,
)


class LawFirmViewSet(viewsets.ModelViewSet):
    serializer_class   = LawFirmSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        tenant = getattr(self.request, "tenant", None)
        if tenant:
            return LawFirm.objects.filter(tenant=tenant)
        return LawFirm.objects.none()

    def perform_create(self, serializer):
        serializer.save(tenant=self.request.tenant)


class AttorneyViewSet(viewsets.ModelViewSet):
    serializer_class   = AttorneySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        if hasattr(self.request.user, "attorney"):
            return Attorney.objects.filter(law_firm=self.request.user.attorney.law_firm)
        return Attorney.objects.none()

    def perform_create(self, serializer):
        serializer.save(law_firm=self.request.user.attorney.law_firm)


class ClientViewSet(viewsets.ModelViewSet):
    serializer_class   = ClientSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        if hasattr(self.request.user, "attorney"):
            return Client.objects.filter(law_firm=self.request.user.attorney.law_firm)
        return Client.objects.none()

    def perform_create(self, serializer):
        serializer.save(law_firm=self.request.user.attorney.law_firm)


class CaseViewSet(viewsets.ModelViewSet):
    serializer_class   = CaseSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """
        FIXED ALIGNMENT:
        - Previously only worked if user had attorney relation
        - Now supports:
            1. Attorney users
            2. Tenant-based fallback (important for admin/staff/system users)
        - Prevents silent Case.objects.none() → which caused frontend empty state
        """

        user = self.request.user

        if not user or not user.is_authenticated:
            return Case.objects.none()

        # 1. Primary path: Attorney-based access
        attorney = getattr(user, "attorney", None)
        if attorney and attorney.law_firm:
            return Case.objects.filter(law_firm=attorney.law_firm)

        # 2. Fallback: Tenant-based access (multi-tenant system safety)
        tenant = getattr(self.request, "tenant", None)
        if tenant and hasattr(tenant, "law_firm"):
            return Case.objects.filter(law_firm=tenant.law_firm)

        # 3. Safe default
        return Case.objects.none()

    def perform_create(self, serializer):
        serializer.save(law_firm=self.request.user.attorney.law_firm)

    # ── Attach or change workflow ─────────────────────────────────────────────

    @action(detail=True, methods=["post"], url_path="attach_workflow")
    def attach_workflow(self, request, pk=None):
        case        = self.get_object()
        template_id = request.data.get("workflow_template_id")

        if not template_id:
            return Response(
                {"error": "workflow_template_id is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            template = WorkflowTemplate.objects.get(id=template_id)
        except WorkflowTemplate.DoesNotExist:
            return Response({"error": "Workflow template not found."}, status=404)

        try:
            updated = CaseWorkflowService.attach_workflow(case, template)
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return Response({
            "message":      f"Workflow '{template.name}' attached.",
            "current_step": updated.current_step.name if updated.current_step else None,
            "status":       updated.status,
        })

    # ── Advance to next step ──────────────────────────────────────────────────

    @action(detail=True, methods=["post"], url_path="advance_step")
    def advance_step(self, request, pk=None):
        case          = self.get_object()
        transition_id = request.data.get("transition_id")

        if not transition_id:
            return Response(
                {"error": "transition_id is required. Call /workflow_status/ first."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            updated = CaseWorkflowService.advance_step(
                case,
                transition_id=int(transition_id)
            )
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return Response({
            "message":               f"Case moved to '{updated.current_step.name}'.",
            "status":                updated.status,
            "current_step":          updated.current_step.name,
            "available_transitions": CaseWorkflowService.get_available_transitions(updated),
        })

    # ── Workflow status ───────────────────────────────────────────────────────

    @action(detail=True, methods=["get"], url_path="workflow_status")
    def workflow_status(self, request, pk=None):
        case = self.get_object()

        if not case.workflow_template_id:
            return Response({
                "workflow":  None,
                "message":   "No workflow attached to this case yet.",
            })

        return Response({
            "workflow":              case.workflow_template.name,
            "status":                case.status,
            "current_step":          case.current_step.name if case.current_step else None,
            "steps":                 CaseWorkflowService.get_all_steps(case),
            "available_transitions": CaseWorkflowService.get_available_transitions(case),
        })


class DocumentViewSet(viewsets.ModelViewSet):
    serializer_class   = DocumentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        if hasattr(self.request.user, "attorney"):
            return Document.objects.filter(case__law_firm=self.request.user.attorney.law_firm)
        return Document.objects.none()

    def perform_create(self, serializer):
        case = serializer.validated_data["case"]
        if case.law_firm != self.request.user.attorney.law_firm:
            raise PermissionError("Cannot upload to a case outside your firm.")
        serializer.save()