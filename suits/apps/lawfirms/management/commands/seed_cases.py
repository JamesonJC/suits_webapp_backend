# scripts/seed_cases.py
from apps.tenants.models import Tenant
from apps.tenants.context import set_current_tenant, clear_current_tenant
from apps.lawfirms.models import LawFirm, Case, Client
from faker import Faker
import random

fake = Faker()
statuses = ["OPEN", "CLOSED", "PENDING", "IN_PROGRESS"]

tenants = Tenant.objects.all()
for tenant in tenants:
    set_current_tenant(tenant)
    law_firms = LawFirm.objects.all()
    
    for firm in law_firms:
        clients = Client.objects.filter(law_firm=firm)
        for j in range(20):
            case = Case.objects.create(
                law_firm=firm,
                client=random.choice(clients),
                case_number=f"{firm.code}-CASE-{j+1}",
                title=fake.catch_phrase(),
                status=random.choice(statuses)
            )
            print(f"✅ Created Case: {case.case_number} (Firm: {firm.name})")
    
    clear_current_tenant()