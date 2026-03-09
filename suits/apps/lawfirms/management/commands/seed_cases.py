# apps/lawfirms/management/commands/seed_cases.py

from django.core.management.base import BaseCommand
from faker import Faker
import random

from apps.tenants.context import set_current_tenant, clear_current_tenant
from apps.lawfirms.models import LawFirm, Client, Case
from apps.tenants.models import Tenant


class Command(BaseCommand):
    help = "Seed 20 random cases per law firm"

    def handle(self, *args, **kwargs):
        fake = Faker()
        tenants = Tenant.objects.all()
        created_count = 0

        if not tenants.exists():
            self.stdout.write(self.style.ERROR("No tenants found. Run seed_tenants first."))
            return

        for tenant in tenants:
            set_current_tenant(tenant)
            law_firms = LawFirm.objects.all()  # TenantManager scopes to current tenant

            for firm in law_firms:
                clients = list(Client.objects.filter(law_firm=firm))
                if not clients:
                    self.stdout.write(
                        self.style.WARNING(f"  No clients in {firm.name}, skipping.")
                    )
                    continue

                for i in range(1, 21):  # 20 cases per firm
                    client = random.choice(clients)
                    Case.objects.create(
                        law_firm=firm,
                        client=client,
                        title=fake.sentence(nb_words=4),
                        # ✅ FIX: Case model field is `code`, confirmed from models.py on disk
                        code=f"{firm.code}-CASE-{i}",
                    )
                    created_count += 1

                self.stdout.write(
                    self.style.SUCCESS(f"  Created 20 cases for {firm.name}")
                )

            clear_current_tenant()

        self.stdout.write(
            self.style.SUCCESS(f"Done. Created {created_count} cases total.")
        )