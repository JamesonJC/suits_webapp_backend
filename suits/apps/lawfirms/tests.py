# apps/lawfirms/tests.py

from django.test import TestCase
from apps.tenants.models import Tenant
from apps.tenants.context import set_current_tenant, clear_current_tenant
from apps.users.models import User
from apps.lawfirms.models import LawFirm, Attorney, Client, Case


class CaseIsolationTest(TestCase):
    def setUp(self):
        # Create two tenants
        self.tenant_a = Tenant.objects.create(name="Tenant A", code="TA")
        self.tenant_b = Tenant.objects.create(name="Tenant B", code="TB")

        # --- LAW FIRM A ---
        set_current_tenant(self.tenant_a)
        self.law_firm_a = LawFirm.objects.create(name="Firm A", code="FIRMA")
        self.user_a = User.objects.create_user(username="attorney_a", password="pass")
        self.attorney_a = Attorney.objects.create(user=self.user_a, law_firm=self.law_firm_a)
        self.client_a = Client.objects.create(law_firm=self.law_firm_a, first_name="Client", last_name="A")
        self.case_a = Case.objects.create(law_firm=self.law_firm_a, client=self.client_a, case_number="A001", title="Case A")
        clear_current_tenant()

        # --- LAW FIRM B ---
        set_current_tenant(self.tenant_b)
        self.law_firm_b = LawFirm.objects.create(name="Firm B", code="FIRMB")
        self.user_b = User.objects.create_user(username="attorney_b", password="pass")
        self.attorney_b = Attorney.objects.create(user=self.user_b, law_firm=self.law_firm_b)
        self.client_b = Client.objects.create(law_firm=self.law_firm_b, first_name="Client", last_name="B")
        self.case_b = Case.objects.create(law_firm=self.law_firm_b, client=self.client_b, case_number="B001", title="Case B")
        clear_current_tenant()

    def test_cannot_see_other_firm_cases(self):
        # Test for Firm A
        set_current_tenant(self.tenant_a)
        cases_for_a = Case.objects.filter(law_firm=self.law_firm_a)
        self.assertIn(self.case_a, cases_for_a)
        self.assertNotIn(self.case_b, cases_for_a)
        clear_current_tenant()

        # Test for Firm B
        set_current_tenant(self.tenant_b)
        cases_for_b = Case.objects.filter(law_firm=self.law_firm_b)
        self.assertIn(self.case_b, cases_for_b)
        self.assertNotIn(self.case_a, cases_for_b)
        clear_current_tenant()