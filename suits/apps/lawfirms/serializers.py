# apps/lawfirms/serializers.py
#
# ─────────────────────────────────────────────────────────────────────────────
# WHAT WAS FIXED IN THIS VERSION:
#
#   PROBLEM — AssertionError on startup: "Relational field must provide a queryset"
#
#     Previous code set workflow_template = PrimaryKeyRelatedField(queryset=None)
#     and then assigned the real queryset in __init__().
#
#     DRF validates PrimaryKeyRelatedField at CLASS DEFINITION time — before
#     any instance is created and before __init__() ever runs. It checks that
#     queryset is not None immediately when the class body is parsed.
#     Setting queryset=None therefore triggers AssertionError at startup,
#     crashing the entire Django process (not just a single request).
#
#     Fix: import WorkflowTemplate at the top of the file and pass it as a
#     direct queryset=WorkflowTemplate.objects.all() on the field. This is the
#     standard DRF pattern. The lazy __init__ override is not needed here
#     because there is no circular import — apps.workflows and apps.lawfirms
#     do not import each other at the model level.
#
# ─────────────────────────────────────────────────────────────────────────────

from rest_framework import serializers
from .models import LawFirm, Attorney, Client, Case, Document

# FIX: direct import — no circular dependency exists here.
# workfows imports nothing from lawfirms at the module level.
from apps.workflows.models import WorkflowTemplate


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
        """
        Auto-inject law_firm and tenant from the requesting attorney's profile.
        The frontend only needs to send: first_name, last_name, email, phone.
        law_firm is derived server-side — never trusted from the request body.
        """
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

    # ── Read-only computed fields ─────────────────────────────────────────────

    # Human-readable name of the current workflow step
    # e.g. "Document Collection" — mirrors case.current_step.name
    current_step_name = serializers.CharField(
        source='current_step.name',
        read_only=True,
        default=None,
    )

    # Human-readable workflow template name — mirrors case.workflow_template.name
    workflow_name = serializers.CharField(
        source='workflow_template.name',
        read_only=True,
        default=None,
    )

    # Full client name: "First Last"
    # Lets the dashboard and case list show client names without a second request.
    client_name = serializers.SerializerMethodField(read_only=True)

    def get_client_name(self, obj):
        if obj.client:
            return f'{obj.client.first_name} {obj.client.last_name}'.strip()
        return None

    # ── Optional writable fields ──────────────────────────────────────────────

    # FIX: queryset=WorkflowTemplate.objects.all() — NOT queryset=None.
    # DRF validates this field at class creation time. queryset=None fails
    # immediately with AssertionError before any request is even received.
    # required=False + allow_null=True makes the field optional so cases can
    # be created without a workflow and one attached later via /attach_workflow/.
    workflow_template = serializers.PrimaryKeyRelatedField(
        queryset=WorkflowTemplate.objects.all(),
        required=False,
        allow_null=True,
    )

    class Meta:
        model  = Case
        fields = [
            'id',
            'code',              # Case reference e.g. "PI-2024-001" — required, unique per firm
            'title',             # Case title / short description — required
            'status',            # Synced to current_step.name automatically — read-only
            'law_firm',          # Set by ViewSet.perform_create(), never from request — read-only
            'client',            # FK to Client — required (send integer ID)
            'client_name',       # Derived: "First Last" — read-only
            'workflow_template', # Optional FK — can be attached later
            'workflow_name',     # Derived: template name — read-only
            'current_step',      # Managed by WorkflowEngine — read-only
            'current_step_name', # Derived: step name — read-only
            'start_date',        # Auto-set on creation — read-only
            'end_date',          # Optional close date — writable
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
        """Case code is required and cannot be blank or whitespace-only."""
        if not value or not str(value).strip():
            raise serializers.ValidationError('Case code is required.')
        return str(value).strip()

    def validate_title(self, value):
        """Case title is required and cannot be blank or whitespace-only."""
        if not value or not str(value).strip():
            raise serializers.ValidationError('Case title is required.')
        return str(value).strip()


class DocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model            = Document
        fields           = '__all__'
        read_only_fields = ('uploaded_at',)

    def validate(self, attrs):
        """
        Ensure the document is being attached to a case in the same firm.
        This runs on create — cross-firm document attachment is blocked here
        before the data reaches the database.
        """
        request  = self.context.get('request')
        case     = attrs.get('case')
        attorney = getattr(request.user, 'attorney', None) if request else None

        if attorney and case and case.law_firm != attorney.law_firm:
            raise serializers.ValidationError(
                'Cannot attach a document to a case outside your firm.'
            )
        return attrs