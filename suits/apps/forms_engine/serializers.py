from rest_framework import serializers
from .models import FormTemplate, FormField, CaseFormSubmission

class FormFieldSerializer(serializers.ModelSerializer):
    class Meta:
        model = FormField
        fields = "__all__"

class FormTemplateSerializer(serializers.ModelSerializer):
    fields = FormFieldSerializer(many=True, read_only=True)

    class Meta:
        model = FormTemplate
        fields = "__all__"

class CaseFormSubmissionCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = CaseFormSubmission
        fields = "__all__"

    def validate(self, attrs):
        template = attrs["template"]
        data = attrs["data"]

        for field in template.fields.all():
            if field.required and field.name not in data:
                raise serializers.ValidationError(
                    {field.name: "This field is required"}
                )
        return attrs