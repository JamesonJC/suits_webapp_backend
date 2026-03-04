# apps/lawfirms/tests.py
from django.urls import reverse
from rest_framework.test import APITestCase
from django.contrib.auth import get_user_model
from apps.tenants.models import Tenant
from apps.tenants.context import set_current_tenant, clear_current_tenant
from .models import LawFirm, Attorney, Client, Case, Document

User = get_user_model()


class LawFirmTenantIsolationTests(APITestCase):

    def setUp(self):
        # --- Create tenants ---
        self.tenant_a = Tenant.objects.create(name="Tenant A", code="TA")
        self.tenant_b = Tenant.objects.create(name="Tenant B", code="TB")

        # --- Create firms in tenant context ---
        set_current_tenant(self.tenant_a)
        self.firm_a = LawFirm.objects.create(name="Firm A", code="FA", tenant=self.tenant_a)
        clear_current_tenant()

        set_current_tenant(self.tenant_b)
        self.firm_b = LawFirm.objects.create(name="Firm B", code="FB", tenant=self.tenant_b)
        clear_current_tenant()

        # --- Create user & attorney ---
        self.user_a = User.objects.create_user(username="usera", password="pass")
        set_current_tenant(self.tenant_a)
        self.attorney_a = Attorney.objects.create(user=self.user_a, law_firm=self.firm_a)
        clear_current_tenant()

        # --- Authenticate via JWT ---
        url = reverse("token_obtain_pair")  # DRF simplejwt endpoint
        response = self.client.post(url, {"username": "usera", "password": "pass"}, format="json")
        self.assertEqual(response.status_code, 200)
        token = response.data["access"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

    def test_client_creation_is_firm_safe(self):
        url = reverse("client-list")
        response = self.client.post(
        reverse("client-list"),
        {
            "first_name": "John",
            "last_name": "Doe",
            # include other required fields if any
        },
        format="json"  # make sure DRF parses it as JSON
        )
        print(response.data)
        self.assertEqual(response.status_code, 201)
        set_current_tenant(self.tenant_a)
        client = Client.objects.get(id=response.data["id"])
        clear_current_tenant()
        self.assertEqual(client.law_firm, self.firm_a)

    def test_cannot_access_other_firm_cases(self):
        set_current_tenant(self.tenant_b)
        client_b = Client.objects.create(first_name="Jane", last_name="Doe", law_firm=self.firm_b)
        Case.objects.create(case_number="001", title="Secret Case", client=client_b, law_firm=self.firm_b)
        clear_current_tenant()

        url = reverse("case-list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 0)

    def test_document_upload_restricted(self):
        set_current_tenant(self.tenant_a)
        client_obj = Client.objects.create(first_name="John", last_name="Doe", law_firm=self.firm_a)
        case_obj = Case.objects.create(case_number="CASE1", title="Test Case", client=client_obj, law_firm=self.firm_a)
        clear_current_tenant()

        set_current_tenant(self.tenant_b)
        client_b = Client.objects.create(first_name="Jane", last_name="Doe", law_firm=self.firm_b)
        case_b = Case.objects.create(case_number="CASE2", title="Other Case", client=client_b, law_firm=self.firm_b)
        clear_current_tenant()

        with self.assertRaises(PermissionError):
            Document.objects.create(case=case_b, filename="file.txt", key="abc", content_type="text/plain")