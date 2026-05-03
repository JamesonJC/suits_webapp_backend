# apps/lawfirms/views.py
#
# ─────────────────────────────────────────────────────────────────────────────
# WORKFLOW API OVERVIEW:
#
#   1. Create a case (workflow_template optional on creation):
#      POST /api/cases/
#      Body: {"code":"PI-001","title":"...","client":3,"workflow_template":2}
#      → Case created, auto-placed on step 1 of the workflow.
#
#   2. See the current step and available next moves:
#      GET /api/cases/{id}/workflow_status/
#      → Returns workflow name, current step, all steps, available transitions.
#
#   3. Attorney picks a transition and advances:
#      POST /api/cases/{id}/advance_step/
#      Body: {"transition_id": 3}
#      → Case moves to the chosen step. Status updates.
#
#   4. Attach or change workflow template:
#      POST /api/cases/{id}/attach_workflow/
#      Body: {"workflow_template_id": 5}
#
# ─────────────────────────────────────────────────────────────────────────────
# WHAT WAS FIXED:
#
#   All ViewSets now check for admin users (is_staff / is_superuser) FIRST and
#   return ALL records using Model.unscoped (the UnscopedManager that bypasses
#   tenant filtering).
#
#   Previously, if an admin had no attorney profile and no tenant on the
#   request, every get_queryset() returned Model.objects.none() — empty data.
#
#   ✅ LawFirmViewSet:  admin → LawFirm.unscoped.all()
#   ✅ AttorneyViewSet: admin → Attorney.unscoped.all()
#   ✅ ClientViewSet:   admin → Client.unscoped.all()
#   ✅ CaseViewSet:     admin → Case.unscoped.all()
#   ✅ DocumentViewSet: admin → Document.unscoped.all()
#
#   The attorney-path and tenant-fallback paths are unchanged for firm users.
# ─────────────────────────────────────────────────────────────────────────────

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


# ── Helper ────────────────────────────────────────────────────────────────────
def _is_admin(user) -> bool:
    """Returns True if the user is a Django staff member or superuser."""
    return bool(user and (user.is_staff or user.is_superuser))


# ── LawFirmViewSet ────────────────────────────────────────────────────────────
class LawFirmViewSet(viewsets.ModelViewSet):
    serializer_class   = LawFirmSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user

        # Admin sees all law firms across all tenants
        if _is_admin(user):
            return LawFirm.unscoped.all()

        # Firm users: filter to their own tenant
        tenant = getattr(self.request, "tenant", None)
        if tenant:
            return LawFirm.objects.filter(tenant=tenant)

        return LawFirm.objects.none()

    def perform_create(self, serializer):
        serializer.save(tenant=self.request.tenant)


# ── AttorneyViewSet ───────────────────────────────────────────────────────────
class AttorneyViewSet(viewsets.ModelViewSet):
    serializer_class   = AttorneySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user

        # Admin sees all attorneys
        if _is_admin(user):
            return Attorney.unscoped.all()

        # Firm users: only attorneys in the same law firm
        if hasattr(user, "attorney"):
            return Attorney.objects.filter(law_firm=user.attorney.law_firm)

        return Attorney.objects.none()

    def perform_create(self, serializer):
        serializer.save(law_firm=self.request.user.attorney.law_firm)


# ── ClientViewSet ─────────────────────────────────────────────────────────────
class ClientViewSet(viewsets.ModelViewSet):
    serializer_class   = ClientSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user

        # Admin sees all clients
        if _is_admin(user):
            return Client.unscoped.all()

        # Firm users: only clients in their law firm
        if hasattr(user, "attorney"):
            return Client.objects.filter(law_firm=user.attorney.law_firm)

        return Client.objects.none()

    def perform_create(self, serializer):
        serializer.save(law_firm=self.request.user.attorney.law_firm)


# ── CaseViewSet ───────────────────────────────────────────────────────────────
class CaseViewSet(viewsets.ModelViewSet):
    serializer_class   = CaseSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """
        Data access hierarchy:
          1. Admin (is_staff or is_superuser)  → all cases, unscoped
          2. Attorney (has user.attorney)       → cases in their law firm
          3. Tenant fallback                    → cases in the request tenant's firm
          4. Safe default                       → empty queryset
        """
        user = self.request.user

        if not user or not user.is_authenticated:
            return Case.objects.none()

        # 1. Admin: sees every case across all tenants
        if _is_admin(user):
            return Case.unscoped.all()

        # 2. Attorney: see cases belonging to their law firm
        attorney = getattr(user, "attorney", None)
        if attorney and attorney.law_firm:
            return Case.objects.filter(law_firm=attorney.law_firm)

        # 3. Tenant fallback (e.g. non-attorney staff within a tenant)
        tenant = getattr(self.request, "tenant", None)
        if tenant and hasattr(tenant, "law_firm"):
            return Case.objects.filter(law_firm=tenant.law_firm)

        return Case.objects.none()

    def perform_create(self, serializer):
        serializer.save(law_firm=self.request.user.attorney.law_firm)

    # ── Custom action: attach a workflow template ─────────────────────────────
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

    # ── Custom action: advance to the next workflow step ─────────────────────
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
                case, transition_id=int(transition_id)
            )
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return Response({
            "message":               f"Case moved to '{updated.current_step.name}'.",
            "status":                updated.status,
            "current_step":          updated.current_step.name,
            "available_transitions": CaseWorkflowService.get_available_transitions(updated),
        })

    # ── Custom action: get full workflow status ───────────────────────────────
    @action(detail=True, methods=["get"], url_path="workflow_status")
    def workflow_status(self, request, pk=None):
        case = self.get_object()

        if not case.workflow_template_id:
            return Response({
                "workflow": None,
                "message":  "No workflow attached to this case yet.",
            })

        return Response({
            "workflow":              case.workflow_template.name,
            "status":                case.status,
            "current_step":          case.current_step.name if case.current_step else None,
            "steps":                 CaseWorkflowService.get_all_steps(case),
            "available_transitions": CaseWorkflowService.get_available_transitions(case),
        })


# ── DocumentViewSet ───────────────────────────────────────────────────────────
class DocumentViewSet(viewsets.ModelViewSet):
    serializer_class   = DocumentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user

        # Admin sees all documents
        if _is_admin(user):
            return Document.unscoped.all()

        # Firm users: only documents attached to cases in their law firm
        if hasattr(user, "attorney"):
            return Document.objects.filter(case__law_firm=user.attorney.law_firm)

        return Document.objects.none()

    def perform_create(self, serializer):
        case = serializer.validated_data["case"]
        if case.law_firm != self.request.user.attorney.law_firm:
            raise PermissionError("Cannot upload to a case outside your firm.")
        serializer.save()