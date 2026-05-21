from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from .models import Task
from .serializers import TaskSerializer

def _is_admin(user):
    return bool(user and (user.is_staff or user.is_superuser))

class TaskViewSet(viewsets.ModelViewSet):
    serializer_class   = TaskSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if not user or not user.is_authenticated:
            return Task.objects.none()
        if _is_admin(user):
            return Task.unscoped.all()
        attorney = getattr(user, 'attorney', None)
        if attorney and attorney.law_firm:
            return Task.objects.filter(law_firm=attorney.law_firm)
        tenant = getattr(self.request, 'tenant', None)
        if tenant:
            try:
                return Task.objects.filter(law_firm=tenant.law_firm)
            except Exception:
                pass
        return Task.objects.none()

    def perform_create(self, serializer):
        user     = self.request.user
        attorney = getattr(user, 'attorney', None)
        if attorney and attorney.law_firm:
            serializer.save(law_firm=attorney.law_firm, tenant=attorney.law_firm.tenant)
        else:
            serializer.save()

    @action(detail=True, methods=['post'], url_path='toggle')
    def toggle(self, request, pk=None):
        task  = self.get_object()
        cycle = [Task.STATUS_PENDING, Task.STATUS_IN_PROGRESS, Task.STATUS_COMPLETED]
        try:
            nxt = cycle[(cycle.index(task.status) + 1) % len(cycle)]
        except ValueError:
            nxt = Task.STATUS_PENDING
        task.status = nxt
        task.save(update_fields=['status', 'updated_at'])
        return Response({'id': task.id, 'status': task.status})