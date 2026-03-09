from django.core.management.base import BaseCommand
from faker import Faker
import random
from apps.tenants.context import set_current_tenant, clear_current_tenant
from apps.lawfirms.models import LawFirm, Client
from apps.tenants.models import Tenant

class Command(BaseCommand):
    help = "Seed random clients per law firm"

    def handle(self, *args, **kwargs):
        fake = Faker()
        tenants = Tenant.objects.all()
        created_count = 0

        if not tenants.exists():
            self.stdout.write(self.style.ERROR("No tenants found. Run seed_tenants_and_lawfirms first."))
            return

        for tenant in tenants:
            set_current_tenant(tenant)
            law_firms = LawFirm.objects.filter(tenant=tenant)

            for firm in law_firms:
                for _ in range(20):  # 20 clients per firm
                    client = Client.objects.create(
                        law_firm=firm,
                        first_name=fake.first_name(),
                        last_name=fake.last_name(),
                        email=fake.email(),
                        phone=fake.phone_number()
                    )
                    created_count += 1
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"✅ Created Client: {client.first_name} {client.last_name} (Firm: {firm.name})"
                        )
                    )

            clear_current_tenant()

        self.stdout.write(
            self.style.SUCCESS(f"🔥 Successfully created {created_count} clients.")
        )