# apps/workflows/tests.py
from rest_framework.test import APITestCase
from apps.tenants.models import Tenant
from .models import WorkflowTemplate

class WorkflowIsolationTest(APITestCase):

    def setUp(self):
        self.tenant_a = Tenant.objects.create(name="Tenant A", code="TA", active=True)
        self.tenant_b = Tenant.objects.create(name="Tenant B", code="TB", active=True)

    def test_workflow_is_tenant_scoped(self):
        # Create workflow for tenant B
        WorkflowTemplate.objects.create(
            tenant=self.tenant_b,
            name="Other Workflow"
        )

        # Manually set the tenant for the request
        self.client.force_authenticate(user=None)  # Or a test user if needed
        self.client.handler._request_middleware = []
        self.client.handler._view_middleware = []
        self.client.handler._exception_middleware = []

        # Directly set tenant in the test client request
        response = self.client.get("/api/workflows/", **{"HTTP_X_TENANT_CODE": "TA"})

        self.assertEqual(len(response.data), 0)