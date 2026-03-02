from django.shortcuts import render

# Create your views here.
from rest_framework import viewsets
from .models import CaseFormSubmission
from .serializers import CaseFormSubmissionSerializer, CaseFormSubmissionCreateSerializer

class CaseFormSubmissionViewSet(viewsets.ModelViewSet):
    queryset = CaseFormSubmission.objects.all()

    def get_serializer_class(self):
        if self.action in ["create", "update"]:
            return CaseFormSubmissionCreateSerializer
        return CaseFormSubmissionSerializer