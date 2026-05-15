# apps/lawfirms/views.py
#
# ─────────────────────────────────────────────────────────────────────────────
# DATA ACCESS RULES — read this before editing any get_queryset():
#
#   ADMIN (is_staff OR is_superuser):
#     - request.tenant is None (TenantMiddleware lets them through without header)
#     - Must use Model.unscoped.all() to bypass TenantManager which returns .none()
#       when no tenant is in thread-local context
#     - LawFirm / Attorney / Client / Case  → extend BaseModel → have .unscoped
#     - Document                            → extends models.Model directly
#                                           → NO .unscoped manager
#                                           → use Document.objects.all() instead
#
#   FIRM USER with attorney profile (user.attorney exists):
#     - TenantManager already scoped by middleware
#     - Filter further by law_firm for tighter isolation
#
#   FIRM USER without attorney profile (support staff, firm admin):
#     - Fall back to filtering by request.tenant → tenant.law_firm
#
# ─────────────────────────────────────────────────────────────────────────────
# WHAT WAS FIXED IN THIS VERSION:
#
#      DocumentViewSet.get_queryset() was calling Document.unscoped.all().
#      Document extends models.Model directly (NOT BaseModel), so it has no
#      .unscoped manager. This caused AttributeError → HTTP 500 on any
#      document request. Fixed to use Document.objects.all() for admin users.
#
#      CaseViewSet — clarified fallback chain with explicit exception handling
#      for the tenant.law_firm reverse accessor.
# ─────────────────────────────────────────────────────────────────────────────

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.workflows.services import CaseWorkflowService
from apps.workflows.models   import WorkflowTemplate
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
    Admin  → all firms across all tenants   (LawFirm extends BaseModel → .unscoped exists)
    Firm   → only their own firm
    """
    serializer_class   = LawFirmSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user

        # Admin: bypass TenantManager — see every firm
        if _is_admin(user):
            return LawFirm.unscoped.all()

        # Firm user: filter to their tenant's firm
        tenant = getattr(self.request, 'tenant', None)
        if tenant:
            return LawFirm.objects.filter(tenant=tenant)

        return LawFirm.objects.none()

    def perform_create(self, serializer):
        serializer.save(tenant=self.request.tenant)


# ── AttorneyViewSet ────────────────────────────────────────────────────────────
class AttorneyViewSet(viewsets.ModelViewSet):
    """
    /api/attorneys/
    Admin  → all attorneys   (Attorney extends BaseModel → .unscoped exists)
    Firm   → attorneys in their law firm only
    """
    serializer_class   = AttorneySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user

        if _is_admin(user):
            return Attorney.unscoped.all()

        attorney = getattr(user, 'attorney', None)
        if attorney:
            return Attorney.objects.filter(law_firm=attorney.law_firm)

        return Attorney.objects.none()

    def perform_create(self, serializer):
        serializer.save(law_firm=self.request.user.attorney.law_firm)


# ── ClientViewSet ──────────────────────────────────────────────────────────────
class ClientViewSet(viewsets.ModelViewSet):
    """
    /api/clients/
    Admin  → all clients   (Client extends BaseModel → .unscoped exists)
    Firm   → clients in their law firm only
    """
    serializer_class   = ClientSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user

        if _is_admin(user):
            return Client.unscoped.all()

        attorney = getattr(user, 'attorney', None)
        if attorney:
            return Client.objects.filter(law_firm=attorney.law_firm)

        # Fallback: non-attorney firm user → filter via tenant
        tenant = getattr(self.request, 'tenant', None)
        if tenant:
            try:
                return Client.objects.filter(law_firm=tenant.law_firm)
            except Exception:
                pass

        return Client.objects.none()

    def perform_create(self, serializer):
        # ClientSerializer.create() injects law_firm + tenant automatically
        serializer.save()


# ── CaseViewSet ────────────────────────────────────────────────────────────────
class CaseViewSet(viewsets.ModelViewSet):
    """
    /api/cases/

    Priority chain for data access:
      1. Admin        → ALL cases via .unscoped  (Case extends BaseModel → safe)
      2. Attorney     → cases in their law firm
      3. Firm staff   → cases in the tenant's law firm (no attorney profile)
      4. Safe default → empty queryset
    """
    serializer_class   = CaseSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user

        if not user or not user.is_authenticated:
            return Case.objects.none()

        # 1. Admin — sees all cases across all tenants
        if _is_admin(user):
            return Case.unscoped.prefetch_related("documents").all()

        # 2. Attorney — sees cases in their law firm
        attorney = getattr(user, 'attorney', None)
        if attorney and attorney.law_firm:
            return Case.objects.filter(law_firm=attorney.law_firm).prefetch_related("documents")

        # 3. Non-attorney firm staff — derive law_firm from the request tenant
        #    Tenant has a OneToOne to LawFirm via LawFirm.tenant FK.
        #    We access it through the related_name "law_firm" on the Tenant.
        tenant = getattr(self.request, 'tenant', None)
        if tenant:
            try:
                return Case.objects.filter(law_firm=tenant.law_firm).prefetch_related("documents")
            except Exception:
                pass

        return Case.objects.none()

    def perform_create(self, serializer):
        """
        Auto-inject law_firm from the attorney's profile.
        Admin users creating cases must pass law_firm in the request body
        because they don't have an attorney profile.
        """
        user     = self.request.user
        attorney = getattr(user, 'attorney', None)
        if attorney and attorney.law_firm:
            serializer.save(law_firm=attorney.law_firm)
        else:
            serializer.save()

    # ── Custom action: attach a workflow template ──────────────────────────────
    @action(detail=True, methods=['post'], url_path='attach_workflow')
    def attach_workflow(self, request, pk=None):
        """
        POST /api/cases/{id}/attach_workflow/
        Body: { "workflow_template_id": <int> }

        Attaches a workflow template to the case and auto-places it on step 1.
        Use this if no workflow was chosen at case creation time.
        """
        case        = self.get_object()
        template_id = request.data.get('workflow_template_id')

        if not template_id:
            return Response(
                {'error': 'workflow_template_id is required.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            template = WorkflowTemplate.objects.get(id=template_id)
        except WorkflowTemplate.DoesNotExist:
            return Response({'error': 'Workflow template not found.'}, status=404)

        try:
            updated = CaseWorkflowService.attach_workflow(case, template)
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return Response({
            'message':      f"Workflow '{template.name}' attached.",
            'current_step': updated.current_step.name if updated.current_step else None,
            'status':       updated.status,
        })

    # ── Custom action: advance to next workflow step ───────────────────────────
    @action(detail=True, methods=['post'], url_path='advance_step')
    def advance_step(self, request, pk=None):
        """
        POST /api/cases/{id}/advance_step/
        Body: { "transition_id": <int> }

        Moves the case forward along the chosen transition.
        Call /workflow_status/ first to see available transition IDs.
        """
        case          = self.get_object()
        transition_id = request.data.get('transition_id')

        if not transition_id:
            return Response(
                {'error': 'transition_id is required. Call /workflow_status/ first.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            updated = CaseWorkflowService.advance_step(
                case, transition_id=int(transition_id)
            )
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return Response({
            'message':               f"Case moved to '{updated.current_step.name}'.",
            'status':                updated.status,
            'current_step':          updated.current_step.name,
            'available_transitions': CaseWorkflowService.get_available_transitions(updated),
        })

    # ── Custom action: get workflow status ─────────────────────────────────────
    @action(detail=True, methods=['get'], url_path='workflow_status')
    def workflow_status(self, request, pk=None):
        """
        GET /api/cases/{id}/workflow_status/
        Returns the current step + all available next transitions.
        """
        case = self.get_object()

        if not case.workflow_template_id:
            return Response({
                'workflow': None,
                'message':  'No workflow attached to this case yet.',
            })

        return Response({
            'workflow':              case.workflow_template.name,
            'status':                case.status,
            'current_step':          case.current_step.name if case.current_step else None,
            'steps':                 CaseWorkflowService.get_all_steps(case),
            'available_transitions': CaseWorkflowService.get_available_transitions(case),
        })


# ── DocumentViewSet ────────────────────────────────────────────────────────────
class DocumentViewSet(viewsets.ModelViewSet):
    """
    /api/documents/

        Document extends models.Model directly (NOT BaseModel).
        It has NO .unscoped manager — using Document.unscoped.all() crashes
        with AttributeError. Admin access uses Document.objects.all() instead.

    Admin  → all documents   (Document.objects.all() — plain manager, no tenant filter)
    Firm   → documents attached to cases in their law firm
    """
    serializer_class   = DocumentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user

        if _is_admin(user):
            # FIX: Document has no .unscoped — use .objects directly.
            # Document.objects is a plain Django manager (no TenantManager override),
            # so this correctly returns all documents without any tenant filter.
            return Document.objects.all()

        attorney = getattr(user, 'attorney', None)
        if attorney:
            return Document.objects.filter(case__law_firm=attorney.law_firm)

        # Fallback for non-attorney firm staff
        tenant = getattr(self.request, 'tenant', None)
        if tenant:
            try:
                return Document.objects.filter(case__law_firm=tenant.law_firm)
            except Exception:
                pass

        return Document.objects.none()

    def perform_create(self, serializer):
        case     = serializer.validated_data.get('case')
        attorney = getattr(self.request.user, 'attorney', None)
        if attorney and case and case.law_firm != attorney.law_firm:
            raise PermissionError('Cannot upload to a case outside your firm.')
        serializer.save()