from rest_framework import serializers
from .models import LawFirm, Attorney, Client, Case, Document


class LawFirmSerializer(serializers.ModelSerializer):
    class Meta:
        model = LawFirm
        fields = "__all__"


class CaseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Case
        fields = "__all__"
        read_only_fields = ("law_firm",)