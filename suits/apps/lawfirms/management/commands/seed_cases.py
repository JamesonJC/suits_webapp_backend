# apps/lawfirms/management/commands/seed_cases.py
from django.core.management.base import BaseCommand
from faker import Faker
import random
from apps.tenants.context import set_current_tenant, clear_current_tenant
from apps.lawfirms.models import LawFirm, Client, Case
from apps.tenants.models import Tenant

class Command(BaseCommand):
    help = "Seed random cases per client"

    def handle(self, *args, **kwargs):
        fake = Faker()
        tenants = Tenant.objects.all()
        created_count = 0

        if not tenants.exists():
            self.stdout.write(self.style.ERROR("No tenants found."))
            return

        for tenant in tenants:
            set_current_tenant(tenant)
            law_firms = LawFirm.objects.all()

            for firm in law_firms:
                clients = list(Client.objects.filter(law_firm=firm))
                if not clients:
                    continue

                for i in range(20):  # 20 cases per firm
                    client = random.choice(clients)
                    case = Case.objects.create(
                        law_firm=firm,
                        client=client,
                        title=fake.sentence(nb_words=4),
                        code=f"{firm.code}-CASE-{i+1}"
                    )
                    created_count += 1
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"✅ Created Case: {case.code} (Firm: {firm.name})"
                        )
                    )

            clear_current_tenant()

        self.stdout.write(
            self.style.SUCCESS(f"🔥 Successfully created {created_count} cases.")
        )