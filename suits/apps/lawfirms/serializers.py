# apps/lawfirms/serializers.py
#
# WHAT CHANGED:
#   ✅ CaseSerializer now includes `client_name` (read-only, derived from
#      client.first_name + last_name). This lets the frontend show the
#      client's name in list views without a separate /clients/ request.

from rest_framework import serializers
from .models import LawFirm, Attorney, Client, Case, Document


class LawFirmSerializer(serializers.ModelSerializer):
    class Meta:
        model  = LawFirm
        fields = "__all__"
        read_only_fields = ("tenant",)


class AttorneySerializer(serializers.ModelSerializer):
    class Meta:
        model  = Attorney
        fields = "__all__"
        read_only_fields = ("law_firm", "user")


class ClientSerializer(serializers.ModelSerializer):
    class Meta:
        model  = Client
        fields = "__all__"
        read_only_fields = ("law_firm", "tenant")

    def create(self, validated_data):
        request = self.context["request"]
        attorney = request.user.attorney
        validated_data["law_firm"] = attorney.law_firm
        validated_data["tenant"]   = attorney.law_firm.tenant
        return super().create(validated_data)


class CaseSerializer(serializers.ModelSerializer):
    # Human-readable step and workflow names (read-only extras)
    current_step_name = serializers.CharField(
        source="current_step.name",
        read_only=True,
        default=None,
    )
    workflow_name = serializers.CharField(
        source="workflow_template.name",
        read_only=True,
        default=None,
    )
    # ✅ NEW: client's full name — derived from the related Client object.
    # Allows the dashboard and case list to show names without a second request.
    client_name = serializers.SerializerMethodField(read_only=True)

    def get_client_name(self, obj):
        """Return "FirstName LastName" or just one of them if the other is blank."""
        if obj.client:
            return f"{obj.client.first_name} {obj.client.last_name}".strip()
        return None

    class Meta:
        model  = Case
        fields = [
            "id",
            "code",
            "title",
            "status",
            "current_step",
            "current_step_name",
            "workflow_template",
            "workflow_name",
            "law_firm",
            "client",
            "client_name",        # ← ADDED: the full client name string
            "start_date",
            "end_date",
        ]
        read_only_fields = (
            "law_firm",
            "status",
            "current_step",
            "current_step_name",
            "client_name",
        )

    def validate_code(self, value):
        if not value:
            raise serializers.ValidationError("Case code is required.")
        return value


class DocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model  = Document
        fields = "__all__"
        read_only_fields = ("uploaded_at",)

    case = serializers.PrimaryKeyRelatedField(
        queryset=Case.objects.all(),
        write_only=True,
    )

    def validate(self, attrs):
        request = self.context.get("request")
        case    = attrs.get("case")
        if request and hasattr(request.user, "attorney"):
            if case.law_firm != request.user.attorney.law_firm:
                raise serializers.ValidationError(
                    "Cannot attach document to a case outside your firm."
                )
        return attrs