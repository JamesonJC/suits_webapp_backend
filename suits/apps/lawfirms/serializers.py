# apps/lawfirms/serializers.py
#
# ─────────────────────────────────────────────────────────────────────────────
# WHAT WAS FIXED:
#
#   CaseSerializer:
#      `law_firm` is now truly read-only — it is set by perform_create in
#        the ViewSet, never accepted from the request body. Previously it was
#        listed in read_only_fields but also in fields as a writable FK,
#        which caused confusing validation behaviour.
#
#      `client_name` is a SerializerMethodField — computed from client.first_name
#        + client.last_name. Lets the dashboard show client names without a
#        separate /clients/ request.
#
#      `workflow_template` is explicitly optional (required=False, allow_null=True)
#        so cases can be created without a workflow and one attached later via
#        POST /api/cases/{id}/attach_workflow/.
#
#   ClientSerializer:
#      create() auto-injects law_firm and tenant from the requesting attorney.
#        This means the frontend only needs to send {first_name, last_name, email}.
#
#   DocumentSerializer:
#      case field is a write-only PrimaryKeyRelatedField — the frontend sends
#        a case ID (integer), and the serializer resolves it to the Case instance.
#        The case is returned in responses as its ID (via the read field).
# ─────────────────────────────────────────────────────────────────────────────

from rest_framework import serializers
from .models import LawFirm, Attorney, Client, Case, Document
from apps.workflows.models import WorkflowTemplate  #  FIX: direct import


class LawFirmSerializer(serializers.ModelSerializer):
    class Meta:
        model            = LawFirm
        fields           = "__all__"
        read_only_fields = ("tenant",)


class AttorneySerializer(serializers.ModelSerializer):
    class Meta:
        model            = Attorney
        fields           = "__all__"
        read_only_fields = ("law_firm", "user")


class ClientSerializer(serializers.ModelSerializer):
    class Meta:
        model            = Client
        fields           = ["id", "first_name", "last_name", "email", "phone", "law_firm"]
        read_only_fields = ("law_firm", "tenant")

    def create(self, validated_data):
        """
        Auto-assign law_firm and tenant from the requesting attorney's profile.
        The frontend only needs to send: first_name, last_name, email, phone.
        """
        request  = self.context["request"]
        attorney = getattr(request.user, "attorney", None)

        if not attorney:
            raise serializers.ValidationError(
                "Only attorneys can create clients. Your account has no attorney profile."
            )

        validated_data["law_firm"] = attorney.law_firm
        validated_data["tenant"]   = attorney.law_firm.tenant
        return super().create(validated_data)


class CaseSerializer(serializers.ModelSerializer):
    # ── Read-only derived fields ──────────────────────────────────────────────

    # Human-readable name of the current workflow step (e.g. "Document Collection")
    current_step_name = serializers.CharField(
        source="current_step.name",
        read_only=True,
        default=None,
    )

    # Human-readable workflow template name (e.g. "Personal Injury Workflow")
    workflow_name = serializers.CharField(
        source="workflow_template.name",
        read_only=True,
        default=None,
    )

    # Full client name — "First Last" — avoids a second API call in lists/dashboard
    client_name = serializers.SerializerMethodField(read_only=True)

    def get_client_name(self, obj):
        if obj.client:
            return f"{obj.client.first_name} {obj.client.last_name}".strip()
        return None

    # ── Writable fields ───────────────────────────────────────────────────────

    # workflow_template is optional: can be attached later via /attach_workflow/
    workflow_template = serializers.PrimaryKeyRelatedField(
        queryset=WorkflowTemplate.objects.all(),  # ✅ FIX: must provide queryset
        required=False,
        allow_null=True,
    )

    class Meta:
        model  = Case
        fields = [
            "id",
            "code",               # Case number / reference (e.g. "PI-2024-001") — required
            "title",              # Case title / short description — required
            "status",             # Derived from current step name — read-only
            "law_firm",           # Set by ViewSet.perform_create() — read-only
            "client",             # FK to Client — required (integer ID in requests)
            "client_name",        # Derived: "First Last" — read-only
            "workflow_template",  # Optional FK to WorkflowTemplate
            "workflow_name",      # Derived: template name — read-only
            "current_step",       # Current workflow step FK — read-only
            "current_step_name",  # Derived: step name — read-only
            "start_date",         # Auto-set on creation — read-only
            "end_date",           # Optional end date — writable
        ]
        read_only_fields = (
            "law_firm",
            "status",
            "current_step",
            "current_step_name",
            "client_name",
            "workflow_name",
            "start_date",
        )

    def validate_code(self, value):
        """Case code cannot be blank."""
        if not value or not value.strip():
            raise serializers.ValidationError("Case code is required.")
        return value.strip()

    def validate_title(self, value):
        """Case title cannot be blank."""
        if not value or not value.strip():
            raise serializers.ValidationError("Case title is required.")
        return value.strip()


class DocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model            = Document
        fields           = "__all__"
        read_only_fields = ("uploaded_at",)

    def validate(self, attrs):
        request  = self.context.get("request")
        case     = attrs.get("case")
        attorney = getattr(request.user, "attorney", None) if request else None

        if attorney and case and case.law_firm != attorney.law_firm:
            raise serializers.ValidationError(
                "Cannot attach a document to a case outside your firm."
            )
        return attrs
