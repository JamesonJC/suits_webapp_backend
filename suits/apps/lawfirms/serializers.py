# apps/lawfirms/serializers.py
#
# ─────────────────────────────────────────────────────────────────────────────
# CHANGES IN THIS VERSION:
#
#  1. document_count  (NEW FIELD on CaseSerializer)
#     — SerializerMethodField that calls obj.documents.count()
#     — Document.case FK has related_name="documents" so the reverse manager
#       is accessible as obj.documents — this is a single SQL COUNT(*) query,
#       not a full queryset load.
#     — Exposed as read-only; shown on each Case card as "12 Documents".
#
#  2. WorkflowTemplatePKField (unchanged — kept lazy to avoid circular import)
#     — The queryset is evaluated inside get_queryset() at request time,
#       never at class-definition / startup time.
#     — Prevents the circular import crash: lawfirms → workflows → lawfirms.
# ─────────────────────────────────────────────────────────────────────────────

from rest_framework import serializers
from .models import LawFirm, Attorney, Client, Case, Document


# ── Lazy FK field for WorkflowTemplate ────────────────────────────────────────
# Import happens inside get_queryset() (request time), not at module level.
# This breaks the circular import: lawfirms.serializers → workflows.models
# → (anything that re-imports lawfirms) → ImportError at startup → 500 everywhere.
class WorkflowTemplatePKField(serializers.PrimaryKeyRelatedField):
    def get_queryset(self):
        from apps.workflows.models import WorkflowTemplate
        return WorkflowTemplate.objects.all()


# ── LawFirmSerializer ──────────────────────────────────────────────────────────
class LawFirmSerializer(serializers.ModelSerializer):
    class Meta:
        model            = LawFirm
        fields           = '__all__'
        read_only_fields = ('tenant',)


# ── AttorneySerializer ─────────────────────────────────────────────────────────
class AttorneySerializer(serializers.ModelSerializer):
    class Meta:
        model            = Attorney
        fields           = '__all__'
        read_only_fields = ('law_firm', 'user')


# ── ClientSerializer ───────────────────────────────────────────────────────────
class ClientSerializer(serializers.ModelSerializer):
    class Meta:
        model            = Client
        fields           = ['id', 'first_name', 'last_name', 'email', 'phone', 'law_firm']
        read_only_fields = ('law_firm', 'tenant')

    def create(self, validated_data):
        """
        Auto-inject law_firm and tenant from the requesting attorney's profile.
        The frontend sends: first_name, last_name, email, phone.
        law_firm and tenant are derived server-side — never trusted from the body.
        """
        request  = self.context['request']
        attorney = getattr(request.user, 'attorney', None)
        if not attorney:
            raise serializers.ValidationError(
                'Only attorneys can create clients. '
                'Your account has no attorney profile.'
            )
        validated_data['law_firm'] = attorney.law_firm
        validated_data['tenant']   = attorney.law_firm.tenant
        return super().create(validated_data)


# ── CaseSerializer ─────────────────────────────────────────────────────────────
class CaseSerializer(serializers.ModelSerializer):

    # Human-readable current workflow step name e.g. "Document Collection"
    current_step_name = serializers.CharField(
        source='current_step.name',
        read_only=True,
        default=None,
    )

    # Human-readable workflow template name e.g. "Personal Injury Workflow"
    workflow_name = serializers.CharField(
        source='workflow_template.name',
        read_only=True,
        default=None,
    )

    # Full client name "First Last" — shown on cards and in the dashboard table
    client_name = serializers.SerializerMethodField(read_only=True)

    def get_client_name(self, obj):
        if obj.client:
            return f'{obj.client.first_name} {obj.client.last_name}'.strip()
        return None

    # ── NEW: document_count ────────────────────────────────────────────────────
    # Number of Document records attached to this case.
    #
    # HOW IT WORKS:
    #   Document.case is a ForeignKey to Case with related_name="documents".
    #   This creates a reverse manager: case_instance.documents  (a RelatedManager).
    #   Calling .count() on a RelatedManager issues a single SQL COUNT(*) query —
    #   it does NOT load all documents into memory.
    #
    # WHY THIS IS THE RIGHT APPROACH (vs annotate in the ViewSet):
    #   - Using annotate(document_count=Count('documents')) in get_queryset()
    #     would also work but couples the annotation to every queryset.
    #   - SerializerMethodField keeps the logic self-contained in the serializer
    #     and is easier to disable/change without touching the ViewSet.
    #   - For large datasets, consider switching to annotate for efficiency.
    #
    # DISPLAYED AS: "12 Documents" on each Cases card.
    document_count = serializers.SerializerMethodField(read_only=True)

    def get_document_count(self, obj):
        """
        Return the number of documents attached to this case.
        Safely returns 0 if the reverse relation doesn't exist (e.g. during tests).
        """
        try:
            return obj.documents.count()
        except Exception:
            return 0

    # Optional FK to workflow template — lazy to avoid circular import
    workflow_template = WorkflowTemplatePKField(required=False, allow_null=True)

    class Meta:
        model  = Case
        fields = [
            'id',
            'code',               # Unique case reference e.g. "PI-2024-001" — required
            'title',              # Case title / description — required
            'status',             # Derived from current workflow step — read-only
            'law_firm',           # Set by ViewSet.perform_create() — read-only
            'client',             # FK to Client (send integer ID) — required
            'client_name',        # "First Last" from client record — read-only
            'workflow_template',  # Optional FK — attachable later via /attach_workflow/
            'workflow_name',      # Template name string — read-only
            'current_step',       # Managed by WorkflowEngine — read-only
            'current_step_name',  # Step name string — read-only
            'start_date',         # Auto-set on creation — read-only
            'end_date',           # Optional close date — writable
            'document_count',     # ← NEW: count of attached documents — read-only
        ]
        read_only_fields = (
            'law_firm',
            'status',
            'current_step',
            'current_step_name',
            'client_name',
            'workflow_name',
            'start_date',
            'document_count',
        )

    def validate_code(self, value):
        if not value or not str(value).strip():
            raise serializers.ValidationError('Case code is required.')
        return str(value).strip()

    def validate_title(self, value):
        if not value or not str(value).strip():
            raise serializers.ValidationError('Case title is required.')
        return str(value).strip()


# ── DocumentSerializer ─────────────────────────────────────────────────────────
class DocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model            = Document
        fields           = '__all__'
        read_only_fields = ('uploaded_at',)

    def validate(self, attrs):
        """Block cross-firm document uploads."""
        request  = self.context.get('request')
        case     = attrs.get('case')
        attorney = getattr(request.user, 'attorney', None) if request else None
        if attorney and case and case.law_firm != attorney.law_firm:
            raise serializers.ValidationError(
                'Cannot attach a document to a case outside your firm.'
            )
        return attrs