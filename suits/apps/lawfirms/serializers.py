from rest_framework import serializers
from .models import LawFirm, Attorney, Client, Case, Document


# ----- LawFirm -----
class LawFirmSerializer(serializers.ModelSerializer):
    class Meta:
        model = LawFirm
        fields = "__all__"
        read_only_fields = ("tenant",)  # tenant assigned automatically in view


# ----- Attorney -----
class AttorneySerializer(serializers.ModelSerializer):
    class Meta:
        model = Attorney
        fields = "__all__"
        read_only_fields = ("law_firm", "user")  # assigned automatically


# ----- Client -----
class ClientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Client
        fields = "__all__"
        read_only_fields = ("law_firm", "tenant")

    def create(self, validated_data):
        request = self.context["request"]
        attorney = request.user.attorney
        validated_data["law_firm"] = attorney.law_firm
        validated_data["tenant"] = attorney.law_firm.tenant
        return super().create(validated_data)

# ----- Case -----
class CaseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Case
        fields = "__all__"
        read_only_fields = ("law_firm",)  # law_firm set in view

    def validate_case_number(self, value):
        if not value:
            raise serializers.ValidationError("Case number is required.")
        return value


# ----- Document -----
class DocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Document
        fields = "__all__"
        read_only_fields = ("uploaded_at",)  # timestamp auto-set

    # case must be validated in view to belong to the firm
    case = serializers.PrimaryKeyRelatedField(
        queryset=Case.objects.all(), write_only=True
    )

    def validate(self, attrs):
        request = self.context.get("request")
        case = attrs.get("case")
        if request and hasattr(request.user, "attorney"):
            if case.law_firm != request.user.attorney.law_firm:
                raise serializers.ValidationError(
                    "Cannot attach document to a case outside your firm."
                )
        return attrs