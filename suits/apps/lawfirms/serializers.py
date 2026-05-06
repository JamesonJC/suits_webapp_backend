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

# New (WHAT CHANGED):
#      CaseSerializer now includes `document_count` — a read-only integer
#      computed from the reverse FK relation: case.documents.count()
#      The Document model has related_name="documents" on its Case FK,
#      so obj.documents.count() is a single DB query.
#      This lets the Cases card UI show "12 Documents" without a separate request.
#
#      WorkflowTemplatePKField uses lazy get_queryset() to avoid the circular
#      import that caused the entire app to return 500 at startup.
#      (lawfirms/serializers.py → workflows/models.py → back to lawfirms)
 
from rest_framework import serializers
from .models import LawFirm, Attorney, Client, Case, Document
 
 
class WorkflowTemplatePKField(serializers.PrimaryKeyRelatedField):
    """
    Lazy-loaded FK field for WorkflowTemplate.
    The import happens inside get_queryset() (called at request time),
    NOT at class definition time, so the circular import is avoided.
    """
    def get_queryset(self):
        from apps.workflows.models import WorkflowTemplate
        return WorkflowTemplate.objects.all()
 
 
class LawFirmSerializer(serializers.ModelSerializer):
    class Meta:
        model            = LawFirm
        fields           = '__all__'
        read_only_fields = ('tenant',)
 
 
class AttorneySerializer(serializers.ModelSerializer):
    class Meta:
        model            = Attorney
        fields           = '__all__'
        read_only_fields = ('law_firm', 'user')
 
 
class ClientSerializer(serializers.ModelSerializer):
    class Meta:
        model            = Client
        fields           = ['id', 'first_name', 'last_name', 'email', 'phone', 'law_firm']
        read_only_fields = ('law_firm', 'tenant')
 
    def create(self, validated_data):
        request  = self.context['request']
        attorney = getattr(request.user, 'attorney', None)
        if not attorney:
            raise serializers.ValidationError(
                'Only attorneys can create clients. Your account has no attorney profile.'
            )
        validated_data['law_firm'] = attorney.law_firm
        validated_data['tenant']   = attorney.law_firm.tenant
        return super().create(validated_data)
 
 
class CaseSerializer(serializers.ModelSerializer):
 
    # Human-readable current workflow step name e.g. "Document Collection"
    current_step_name = serializers.CharField(
        source='current_step.name', read_only=True, default=None,
    )
 
    # Human-readable workflow template name e.g. "Personal Injury Workflow"
    workflow_name = serializers.CharField(
        source='workflow_template.name', read_only=True, default=None,
    )
 
    # Full client name "First Last" — shown in the Cases card
    client_name = serializers.SerializerMethodField(read_only=True)
 
    # NEW: document count — shown as "12 Documents" on each card
    # Uses the reverse relation: Document.case FK with related_name="documents"
    # obj.documents is a RelatedManager; .count() is a single cheap SQL COUNT(*)
    document_count = serializers.SerializerMethodField(read_only=True)
 
    workflow_template = WorkflowTemplatePKField(required=False, allow_null=True)
 
    def get_client_name(self, obj):
        if obj.client:
            return f'{obj.client.first_name} {obj.client.last_name}'.strip()
        return None
 
    def get_document_count(self, obj):
        try:
            return obj.documents.count()
        except Exception:
            return 0
 
    class Meta:
        model  = Case
        fields = [
            'id', 'code', 'title', 'status',
            'law_firm',
            'client', 'client_name',
            'workflow_template', 'workflow_name',
            'current_step', 'current_step_name',
            'start_date', 'end_date',
            'document_count',     # ← NEW
        ]
        read_only_fields = (
            'law_firm', 'status',
            'current_step', 'current_step_name',
            'client_name', 'workflow_name',
            'start_date', 'document_count',
        )
 
    def validate_code(self, value):
        if not value or not str(value).strip():
            raise serializers.ValidationError('Case code is required.')
        return str(value).strip()
 
    def validate_title(self, value):
        if not value or not str(value).strip():
            raise serializers.ValidationError('Case title is required.')
        return str(value).strip()
 
 
class DocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model            = Document
        fields           = '__all__'
        read_only_fields = ('uploaded_at',)
 
    def validate(self, attrs):
        request  = self.context.get('request')
        case     = attrs.get('case')
        attorney = getattr(request.user, 'attorney', None) if request else None
        if attorney and case and case.law_firm != attorney.law_firm:
            raise serializers.ValidationError(
                'Cannot attach a document to a case outside your firm.'
            )
        return attrs