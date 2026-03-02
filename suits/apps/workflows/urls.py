from rest_framework.routers import DefaultRouter
from .views import WorkflowTemplateViewSet

router = DefaultRouter()
router.register("workflow-templates", WorkflowTemplateViewSet, basename="workflowtemplate")

urlpatterns = router.urls