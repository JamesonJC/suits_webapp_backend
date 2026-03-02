from django.shortcuts import render

# Create your views here.
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import Job, Attachment
from apps.core.r2_client import upload_file
from apps.tenants.context import get_current_tenant
from rest_framework.permissions import IsAuthenticated

from apps.core.r2_client import upload_file, generate_r2_key
from apps.rbac.permissions import HasPlatformPermission

class JobViewSet(viewsets.ModelViewSet):
    queryset = Job.objects.all()
    permission_classes = [IsAuthenticated, HasPlatformPermission]
    # ...serializer_class, permissions...

    @action(detail=True, methods=["post"])
    def upload_attachment(self, request, pk=None):
        job = self.get_object()
        file_obj = request.FILES["file"]
        tenant = get_current_tenant()
        key = f"tenant_{tenant.id}/job_{job.id}/{file_obj.name}"

        upload_file(file_obj, key)

        attachment = Attachment.objects.create(
            job=job,
            filename=file_obj.name,
            key=key,
            content_type=file_obj.content_type,
            size=file_obj.size
        )
        return Response({"id": attachment.id, "key": attachment.key})

    @action(detail=True, methods=["get"], url_path="download")
    def download_attachment(self, request, pk=None):
        attachment = Attachment.objects.get(id=pk)

        from apps.core.r2_client import generate_signed_url
        url = generate_signed_url(attachment.key, expires=3600)

        return Response({"url": url})