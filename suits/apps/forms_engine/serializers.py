from rest_framework import serializers
from .models import FormTemplate, FormField, CaseFormSubmission


class FormFieldSerializer(serializers.ModelSerializer):
    class Meta:
        model = FormField
        fields = "__all__"


class FormTemplateSerializer(serializers.ModelSerializer):
    """
    Returns the template with all its fields nested.
    Fields are read-only here — manage them via their own endpoint.
    """
    fields = FormFieldSerializer(many=True, read_only=True)

    class Meta:
        model = FormTemplate
        fields = "__all__"
        read_only_fields = ("tenant",)


# ---- Read serializer (used in list/retrieve) ----
class CaseFormSubmissionSerializer(serializers.ModelSerializer):
    """
    Simple read serializer — returns all fields as-is.
    """
    class Meta:
        model = CaseFormSubmission
        fields = "__all__"


# ---- Write serializer (used in create/update) ----
class CaseFormSubmissionCreateSerializer(serializers.ModelSerializer):
    """
    Write serializer with field validation.
    Checks that all required fields in the template are present in the submitted data.
    """
    class Meta:
        model = CaseFormSubmission
        fields = "__all__"

    def validate(self, attrs):
        template = attrs.get("template")
        data = attrs.get("data", {})

        # Check every required field in the template is present in the submission
        if template:
            for field in template.fields.all():
                if field.required and field.name not in data:
                    raise serializers.ValidationError(
                        {field.name: f"This field is required by the form template."}
                    )

        return attrs