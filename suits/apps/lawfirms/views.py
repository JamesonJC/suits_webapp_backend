# apps/lawfirms/views.py

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
            return Attorney.objects.filter(
                law_firm=self.request.user.attorney.law_firm
            )
        return Attorney.objects.none()

    def perform_create(self, serializer):
        serializer.save(law_firm=self.request.user.attorney.law_firm)


class ClientViewSet(viewsets.ModelViewSet):
    serializer_class   = ClientSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        if hasattr(self.request.user, "attorney"):
            return Client.objects.filter(
                law_firm=self.request.user.attorney.law_firm
            )
        return Client.objects.none()

    def perform_create(self, serializer):
        serializer.save(law_firm=self.request.user.attorney.law_firm)


class CaseViewSet(viewsets.ModelViewSet):
    """
    Standard CRUD for Cases plus three workflow actions:

    POST /api/cases/{id}/attach_workflow/
        Body: { "workflow_template_id": <int> }
        Attaches a workflow and moves the case to step 1.

    POST /api/cases/{id}/advance_step/
        Body: { "context": { "decision": "APPROVED" } }  ← optional
        Moves the case to the next workflow step.
        Pass a context dict to trigger conditional (branching) transitions.

    GET  /api/cases/{id}/workflow_status/
        Returns the current step, all steps, and available next transitions.
        Use this to render a progress bar and action buttons in the frontend.
    """
    serializer_class   = CaseSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        if hasattr(self.request.user, "attorney"):
            return Case.objects.filter(
                law_firm=self.request.user.attorney.law_firm
            )
        return Case.objects.none()

    def perform_create(self, serializer):
        serializer.save(law_firm=self.request.user.attorney.law_firm)

    # ── Action 1: Attach Workflow ─────────────────────────────────────────────

    @action(detail=True, methods=["post"], url_path="attach_workflow")
    def attach_workflow(self, request, pk=None):
        """
        POST /api/cases/{id}/attach_workflow/
        Body: { "workflow_template_id": 3 }

        Attaches the specified WorkflowTemplate to this case and moves it
        to the first step. The case status updates to the first step's name.
        """
        case = self.get_object()

        template_id = request.data.get("workflow_template_id")
        if not template_id:
            return Response(
                {"error": "workflow_template_id is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            template = WorkflowTemplate.objects.get(id=template_id)
        except WorkflowTemplate.DoesNotExist:
            return Response(
                {"error": "WorkflowTemplate not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        try:
            updated_case = CaseWorkflowService.attach_workflow(case, template)
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return Response({
            "message":      f"Workflow '{template.name}' attached.",
            "status":       updated_case.status,
            "current_step": updated_case.current_step.name,
        })

    # ── Action 2: Advance Step ────────────────────────────────────────────────

    @action(detail=True, methods=["post"], url_path="advance_step")
    def advance_step(self, request, pk=None):
        """
        POST /api/cases/{id}/advance_step/
        Body (optional): { "context": { "decision": "APPROVED" } }

        Moves the case to the next workflow step.
        - No body / empty context → follows the default/linear transition.
        - With context dict      → evaluates branching conditions.

        Example for an approval workflow:
            POST body: { "context": { "decision": "REJECTED" } }
            → Case moves to the "Rejection Review" step instead of "Processing".
        """
        case = self.get_object()
        context = request.data.get("context", {})

        try:
            updated_case = CaseWorkflowService.advance_step(case, context=context)
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        # Also return available next transitions so the client can update buttons
        available = CaseWorkflowService.get_available_transitions(updated_case)

        return Response({
            "message":                f"Case advanced to '{updated_case.current_step.name}'.",
            "status":                 updated_case.status,
            "current_step":           updated_case.current_step.name,
            "available_transitions":  available,
        })

    # ── Action 3: Workflow Status ─────────────────────────────────────────────

    @action(detail=True, methods=["get"], url_path="workflow_status")
    def workflow_status(self, request, pk=None):
        """
        GET /api/cases/{id}/workflow_status/

        Returns everything the frontend needs to render:
          - current step name and order
          - full list of steps (with is_current flag) for a progress bar
          - available transitions (for "Approve"/"Reject" buttons)
        """
        case = self.get_object()

        if not case.workflow_template:
            return Response({
                "workflow": None,
                "message": "No workflow attached to this case yet.",
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
            return Document.objects.filter(
                case__law_firm=self.request.user.attorney.law_firm
            )
        return Document.objects.none()

    def perform_create(self, serializer):
        case = serializer.validated_data["case"]
        if case.law_firm != self.request.user.attorney.law_firm:
            raise PermissionError("Cannot upload to a case outside your firm")
        serializer.save()