from django.shortcuts import render

# Create your views here.
from rest_framework import viewsets
from .models import Case
from .serializers import CaseSerializer

class CaseViewSet(viewsets.ModelViewSet):
    serializer_class = CaseSerializer
    queryset = Case.objects.all()  # Tenant-safe automatically