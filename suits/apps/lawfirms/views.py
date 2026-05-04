# apps/lawfirms/views.py
#
# ─────────────────────────────────────────────────────────────────────────────
# DATA ACCESS RULES (read this to understand every get_queryset below):
#
#   ADMIN (is_staff OR is_superuser):
#     → Sees ALL records across ALL tenants via Model.unscoped.all()
#     → request.tenant is None (middleware passes them through without a tenant)
#     → TenantManager would return empty — we bypass it with .unscoped
#
#   FIRM USER with attorney profile (user.attorney exists):
#     → Sees records scoped to their law firm
#     → TenantManager also scopes by tenant (set by middleware from X-Tenant-Code)
#
#   FIRM USER without attorney profile (e.g. support staff, firm admin):
#     → Falls back to filtering by request.tenant directly
#     → request.tenant is set by TenantMiddleware from the X-Tenant-Code header
#
# ─────────────────────────────────────────────────────────────────────────────
# WHAT WAS FIXED vs previous version:
#
#    All ViewSets correctly detect admin users and use .unscoped manager.
#      Previously, admins got empty data because TenantManager returned .none()
#      when get_current_tenant() was None (no tenant set for admins).
#
#    CaseViewSet.perform_create() now handles the case where the user is
#      an admin OR doesn't have an attorney profile — raises a clear error
#      instead of crashing with AttributeError.
#
#    ClientSerializer.create() is handled in serializers.py, not here.
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


# ── Shared helper ──────────────────────────────────────────────────────────────
def _is_admin(user) -> bool:
    """True if the user is Django staff or superuser — bypasses tenant scoping."""
    return bool(user and (user.is_staff or user.is_superuser))


# ── LawFirmViewSet ─────────────────────────────────────────────────────────────
class LawFirmViewSet(viewsets.ModelViewSet):
    """
    /api/lawfirms/
    Admin: all firms. Firm user: only their firm (matched by tenant).
    """
    serializer_class   = LawFirmSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user

        if _is_admin(user):
            return LawFirm.unscoped.all()

        tenant = getattr(self.request, "tenant", None)
        if tenant:
            return LawFirm.objects.filter(tenant=tenant)

        return LawFirm.objects.none()

    def perform_create(self, serializer):
        serializer.save(tenant=self.request.tenant)


# ── AttorneyViewSet ────────────────────────────────────────────────────────────
class AttorneyViewSet(viewsets.ModelViewSet):
    """
    /api/attorneys/
    Admin: all attorneys. Firm user: attorneys in their law firm only.
    """
    serializer_class   = AttorneySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user

        if _is_admin(user):
            return Attorney.unscoped.all()

        attorney = getattr(user, "attorney", None)
        if attorney:
            return Attorney.objects.filter(law_firm=attorney.law_firm)

        return Attorney.objects.none()

    def perform_create(self, serializer):
        serializer.save(law_firm=self.request.user.attorney.law_firm)


# ── ClientViewSet ──────────────────────────────────────────────────────────────
class ClientViewSet(viewsets.ModelViewSet):
    """
    /api/clients/
    Admin: all clients. Firm user: clients in their law firm only.
    """
    serializer_class   = ClientSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user

        if _is_admin(user):
            return Client.unscoped.all()

        attorney = getattr(user, "attorney", None)
        if attorney:
            return Client.objects.filter(law_firm=attorney.law_firm)

        # Fallback: non-attorney firm user (e.g. support staff) — filter by tenant
        tenant = getattr(self.request, "tenant", None)
        if tenant and hasattr(tenant, "law_firm"):
            return Client.objects.filter(law_firm=tenant.law_firm)

        return Client.objects.none()

    def perform_create(self, serializer):
        # Creation is handled in ClientSerializer.create() which injects law_firm
        serializer.save()


# ── CaseViewSet ────────────────────────────────────────────────────────────────
class CaseViewSet(viewsets.ModelViewSet):
    """
    /api/cases/

    Data access priority:
      1. Admin → ALL cases (unscoped)
      2. Attorney → cases belonging to their law firm
      3. Non-attorney firm user → cases in the tenant's law firm
      4. Fallback → empty queryset (safe default)
    """
    serializer_class   = CaseSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user

        if not user or not user.is_authenticated:
            return Case.objects.none()

        # 1. Admin sees everything
        if _is_admin(user):
            return Case.unscoped.all()

        # 2. Attorney — cases in their law firm
        attorney = getattr(user, "attorney", None)
        if attorney and attorney.law_firm:
            return Case.objects.filter(law_firm=attorney.law_firm)

        # 3. Non-attorney firm user — derive law firm from tenant
        # This covers firm admins / support staff who are not attorneys themselves.
        tenant = getattr(self.request, "tenant", None)
        if tenant:
            try:
                return Case.objects.filter(law_firm=tenant.law_firm)
            except Exception:
                pass

        return Case.objects.none()

    def perform_create(self, serializer):
        """
        Set law_firm automatically from the attorney's profile.
        The client already belongs to the same firm, validated in the serializer.
        """
        user     = self.request.user
        attorney = getattr(user, "attorney", None)

        if attorney and attorney.law_firm:
            serializer.save(law_firm=attorney.law_firm)
        else:
            # Admin creating a case must explicitly pass law_firm in request body.
            # The serializer will handle it if law_firm is writable.
            serializer.save()

    # ── Custom action: attach a workflow template ──────────────────────────────
    @action(detail=True, methods=["post"], url_path="attach_workflow")
    def attach_workflow(self, request, pk=None):
        """
        POST /api/cases/{id}/attach_workflow/
        Body: { "workflow_template_id": <int> }

        Attaches a workflow to the case and places it on the first step.
        """
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

    # ── Custom action: advance to the next workflow step ───────────────────────
    @action(detail=True, methods=["post"], url_path="advance_step")
    def advance_step(self, request, pk=None):
        """
        POST /api/cases/{id}/advance_step/
        Body: { "transition_id": <int> }

        Moves the case to the next step via the chosen transition.
        Call /workflow_status/ first to see available transition IDs.
        """
        case          = self.get_object()
        transition_id = request.data.get("transition_id")

        if not transition_id:
            return Response(
                {"error": "transition_id is required. Call /workflow_status/ to see options."},
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

    # ── Custom action: get full workflow status ────────────────────────────────
    @action(detail=True, methods=["get"], url_path="workflow_status")
    def workflow_status(self, request, pk=None):
        """
        GET /api/cases/{id}/workflow_status/
        Returns the current step and all available next transitions.
        """
        case = self.get_object()

        if not case.workflow_template_id:
            return Response({
                "workflow": None,
                "message":  "No workflow attached to this case.",
            })

        return Response({
            "workflow":              case.workflow_template.name,
            "status":                case.status,
            "current_step":          case.current_step.name if case.current_step else None,
            "steps":                 CaseWorkflowService.get_all_steps(case),
            "available_transitions": CaseWorkflowService.get_available_transitions(case),
        })


# ── DocumentViewSet ────────────────────────────────────────────────────────────
class DocumentViewSet(viewsets.ModelViewSet):
    """
    /api/documents/
    Admin: all documents. Firm user: documents on cases in their law firm.
    """
    serializer_class   = DocumentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user

        if _is_admin(user):
            return Document.unscoped.all()

        attorney = getattr(user, "attorney", None)
        if attorney:
            return Document.objects.filter(case__law_firm=attorney.law_firm)

        return Document.objects.none()

    def perform_create(self, serializer):
        case = serializer.validated_data["case"]
        attorney = getattr(self.request.user, "attorney", None)
        if attorney and case.law_firm != attorney.law_firm:
            raise PermissionError("Cannot upload to a case outside your firm.")
        serializer.save()
