from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from .models import Case
from .serializers import CaseSerializer
from .models import LawFirm
from .serializers import LawFirmSerializer

class LawFirmViewSet(viewsets.ModelViewSet):
    queryset = LawFirm.objects.all()
    serializer_class = LawFirmSerializer
    permission_classes = [IsAuthenticated]

class CaseViewSet(viewsets.ModelViewSet):
    serializer_class = CaseSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """
        Only return cases belonging to the logged-in user's law firm.
        """
        user = self.request.user

        if not hasattr(user, "attorney"):
            return Case.objects.none()

        return Case.objects.filter(
            law_firm=user.attorney.law_firm
        )

    def perform_create(self, serializer):
        """
        Automatically assign law_firm from logged-in attorney.
        Prevent client from spoofing firm.
        """
        user = self.request.user

        serializer.save(
            law_firm=user.attorney.law_firm
        )