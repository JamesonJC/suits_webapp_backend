# scripts/seed_clients.py
from apps.tenants.models import Tenant
from apps.tenants.context import set_current_tenant, clear_current_tenant
from apps.lawfirms.models import LawFirm, Client
from faker import Faker

fake = Faker()

tenants = Tenant.objects.all()
for tenant in tenants:
    set_current_tenant(tenant)
    law_firms = LawFirm.objects.all()
    
    for firm in law_firms:
        for _ in range(10):
            client = Client.objects.create(
                law_firm=firm,
                first_name=fake.first_name(),
                last_name=fake.last_name(),
                email=fake.email(),
                phone=fake.phone_number()
            )
            print(f"✅ Created Client: {client.first_name} {client.last_name} (Firm: {firm.name})")
    
    clear_current_tenant()