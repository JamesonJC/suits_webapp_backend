# apps/lawfirms/serializers.py
#
# ─────────────────────────────────────────────────────────────────────────────
# ROOT CAUSE OF THE LOGIN 500 FIXED HERE:
#
#   Previous version:
#     from apps.workflows.models import WorkflowTemplate  ← module-level import
#     ...
#     workflow_template = serializers.PrimaryKeyRelatedField(
#         queryset=WorkflowTemplate.objects.all(),         ← evaluated at class definition
#     )
#
#   WHY THIS CAUSED A 500 ON EVERY ENDPOINT (including login):
#
#     Django imports ALL app modules at startup. The import chain was:
#       Django startup
#       → loads apps.lawfirms (serializers.py is imported by admin.py or views.py)
#       → serializers.py runs "from apps.workflows.models import WorkflowTemplate"
#       → Django starts loading apps.workflows.models
#       → workflows/models.py likely imports or references lawfirms models
#       → lawfirms models are still mid-import → circular import → ImportError
#
#     When any app crashes at startup, Django can't build its URL dispatcher.
#     Every request — including GET / and POST /api/auth/login/ — returns 500
#     because the app server itself is broken, not just one endpoint.
#
#   THE FIX — use get_queryset() override:
#
#     class WorkflowTemplatePKField(serializers.PrimaryKeyRelatedField):
#         def get_queryset(self):
#             from apps.workflows.models import WorkflowTemplate  ← lazy import
#             return WorkflowTemplate.objects.all()
#
#     The import now happens at REQUEST TIME (when get_queryset() is called),
#     not at CLASS DEFINITION time. By request time, ALL apps are fully loaded
#     so there's no circular dependency. This is the DRF-recommended pattern
#     for cross-app FK fields that risk circular imports.
#
#   WHY NOT queryset=WorkflowTemplate.objects.all() AT CLASS LEVEL:
#     Even when the import itself succeeds (no circular import crash), calling
#     .objects.all() at class definition time can fail during Django's app
#     loading phase before migrations have run, or when the DB isn't available
#     (e.g. first deploy). get_queryset() is always safer.
# ─────────────────────────────────────────────────────────────────────────────

from rest_framework import serializers
from .models import LawFirm, Attorney, Client, Case, Document

# NOTE: WorkflowTemplate is NOT imported at module level.
# It is imported lazily inside WorkflowTemplatePKField.get_queryset().
# This breaks the circular import chain that caused every endpoint to 500.


# ── Custom PrimaryKeyRelatedField for WorkflowTemplate ────────────────────────
# This pattern is the DRF-recommended way to handle cross-app FK fields
# that would otherwise create circular imports at the module level.
class WorkflowTemplatePKField(serializers.PrimaryKeyRelatedField):
    """
    Lazy-loaded PrimaryKeyRelatedField for WorkflowTemplate.

    get_queryset() is called at request time (not class definition time),
    so the import of WorkflowTemplate happens after all apps are fully loaded.
    This eliminates the circular import: lawfirms → workflows → lawfirms.
    """
    def get_queryset(self):
        # Lazy import — only runs when a request is processed, never at startup
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
        Frontend only needs to send: first_name, last_name, email, phone.
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

    # ── Read-only computed / derived fields ────────────────────────────────────

    # Human-readable current workflow step name, e.g. "Document Collection"
    current_step_name = serializers.CharField(
        source='current_step.name',
        read_only=True,
        default=None,
    )

    # Human-readable workflow template name, e.g. "Personal Injury Workflow"
    workflow_name = serializers.CharField(
        source='workflow_template.name',
        read_only=True,
        default=None,
    )

    # Full client name "First Last" — so the dashboard can show names without
    # making a separate /clients/{id}/ request for every row.
    client_name = serializers.SerializerMethodField(read_only=True)

    def get_client_name(self, obj):
        if obj.client:
            return f'{obj.client.first_name} {obj.client.last_name}'.strip()
        return None

    # ── Writable optional field ────────────────────────────────────────────────

    # FIX: Uses WorkflowTemplatePKField (lazy import) instead of a
    # module-level import + queryset=WorkflowTemplate.objects.all().
    # required=False → case can be created without a workflow, attached later.
    # allow_null=True → frontend can explicitly send null to clear the workflow.
    workflow_template = WorkflowTemplatePKField(
        required=False,
        allow_null=True,
    )

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
        ]
        read_only_fields = (
            'law_firm',
            'status',
            'current_step',
            'current_step_name',
            'client_name',
            'workflow_name',
            'start_date',
        )

    def validate_code(self, value):
        """Case reference code — required, stripped of whitespace."""
        if not value or not str(value).strip():
            raise serializers.ValidationError('Case code is required.')
        return str(value).strip()

    def validate_title(self, value):
        """Case title — required, stripped of whitespace."""
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
        """
        Block cross-firm document attachment.
        Attorneys can only upload documents to cases in their own law firm.
        """
        request  = self.context.get('request')
        case     = attrs.get('case')
        attorney = getattr(request.user, 'attorney', None) if request else None

        if attorney and case and case.law_firm != attorney.law_firm:
            raise serializers.ValidationError(
                'Cannot attach a document to a case outside your firm.'
            )
        return attrs