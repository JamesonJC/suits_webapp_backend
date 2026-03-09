# apps/workflows/urls.py
#
# All workflow-related endpoints live here.
# This file is included in config/urls.py via:
#   path("api/", include("apps.workflows.urls"))
#
# Resulting URLs:
#   /api/workflow-templates/           CRUD for templates
#   /api/workflow-templates/{id}/      detail/update/delete
#   /api/steps/                        CRUD for steps
#   /api/steps/{id}/                   detail/update/delete
#   /api/transitions/                  CRUD for branching transitions
#   /api/transitions/{id}/             detail/update/delete

from rest_framework.routers import DefaultRouter
from .views import WorkflowTemplateViewSet, WorkflowStepViewSet, WorkflowTransitionViewSet

router = DefaultRouter()
router.register(r"workflow-templates", WorkflowTemplateViewSet, basename="workflowtemplate")
router.register(r"steps",             WorkflowStepViewSet,      basename="workflowstep")
router.register(r"transitions",       WorkflowTransitionViewSet, basename="workflowtransition")

urlpatterns = router.urls