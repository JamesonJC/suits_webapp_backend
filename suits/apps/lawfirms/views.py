from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from .models import LawFirm, Attorney, Client, Case, Document
from .serializers import (
    LawFirmSerializer,
    AttorneySerializer,
    ClientSerializer,
    CaseSerializer,
    DocumentSerializer
)


# ----- LawFirm -----
class LawFirmViewSet(viewsets.ModelViewSet):
    serializer_class = LawFirmSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        tenant = getattr(self.request, "tenant", None)
        if tenant:
            return LawFirm.objects.filter(tenant=tenant)
        return LawFirm.objects.none()

    def perform_create(self, serializer):
        serializer.save(tenant=self.request.tenant)


# ----- Attorney -----
class AttorneyViewSet(viewsets.ModelViewSet):
    serializer_class = AttorneySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        if hasattr(self.request.user, "attorney"):
            firm = self.request.user.attorney.law_firm
            return Attorney.objects.filter(law_firm=firm)
        return Attorney.objects.none()

    def perform_create(self, serializer):
        serializer.save(law_firm=self.request.user.attorney.law_firm)


# ----- Client -----
class ClientViewSet(viewsets.ModelViewSet):
    serializer_class = ClientSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        if hasattr(self.request.user, "attorney"):
            firm = self.request.user.attorney.law_firm
            return Client.objects.filter(law_firm=firm)
        return Client.objects.none()

    def perform_create(self, serializer):
        serializer.save(law_firm=self.request.user.attorney.law_firm)


# ----- Case -----
class CaseViewSet(viewsets.ModelViewSet):
    serializer_class = CaseSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        if hasattr(self.request.user, "attorney"):
            firm = self.request.user.attorney.law_firm
            return Case.objects.filter(law_firm=firm)
        return Case.objects.none()

    def perform_create(self, serializer):
        serializer.save(law_firm=self.request.user.attorney.law_firm)


# ----- Document -----
class DocumentViewSet(viewsets.ModelViewSet):
    serializer_class = DocumentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        if hasattr(self.request.user, "attorney"):
            firm = self.request.user.attorney.law_firm
            return Document.objects.filter(case__law_firm=firm)
        return Document.objects.none()

    def perform_create(self, serializer):
        # case must belong to user's law firm
        case = serializer.validated_data["case"]
        if case.law_firm != self.request.user.attorney.law_firm:
            raise PermissionError("Cannot upload to a case outside your firm")
        serializer.save()