# apps/forms_engine/views.py

from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from .models import CaseFormSubmission
# ✅ FIX: The original imported `CaseFormSubmissionSerializer` which does not
#         exist in serializers.py — only `CaseFormSubmissionCreateSerializer` does.
#         Importing a non-existent name causes an ImportError on server startup,
#         which takes down the entire Django process.
from .serializers import CaseFormSubmissionCreateSerializer


class CaseFormSubmissionViewSet(viewsets.ModelViewSet):
    """
    Handles form submissions for cases.
    The create/update path uses the validating serializer that checks required fields.
    The read path (list, retrieve) uses the same serializer — it works fine for reads.
    """
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # Scope to the current tenant via TenantManager on BaseModel
        return CaseFormSubmission.objects.all()

    def get_serializer_class(self):
        return CaseFormSubmissionCreateSerializer