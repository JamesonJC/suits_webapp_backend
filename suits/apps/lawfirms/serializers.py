# apps/lawfirms/serializers.py

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
    # Read-only extras so the client always knows where the case is
    # without needing a separate /workflow_status/ call for basic display
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

    class Meta:
        model  = Case
        fields = [
            "id",
            "code",
            "title",
            "status",               # always mirrors current_step.name
            "current_step",         # FK id (writable to reassign manually)
            "current_step_name",    # human-readable step name (read-only)
            "workflow_template",    # FK id
            "workflow_name",        # human-readable template name (read-only)
            "law_firm",
            "client",
            "start_date",
            "end_date",
        ]
        read_only_fields = ("law_firm", "status", "current_step", "current_step_name")

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