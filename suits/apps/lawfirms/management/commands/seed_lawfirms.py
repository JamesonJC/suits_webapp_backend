from django.core.management.base import BaseCommand
from faker import Faker

from apps.tenants.models import Tenant
from apps.tenants.context import set_current_tenant, clear_current_tenant
from apps.lawfirms.models import LawFirm


class Command(BaseCommand):
    help = "Seed one law firm per tenant"

    def handle(self, *args, **kwargs):
        fake = Faker()
        tenants = Tenant.objects.all()

        if not tenants.exists():
            self.stdout.write(self.style.ERROR("No tenants found."))
            return

        created = 0

        for i, tenant in enumerate(tenants, start=1):
            set_current_tenant(tenant)

            # Avoid duplicates
            if LawFirm.objects.filter(tenant=tenant).exists():
                clear_current_tenant()
                continue

            LawFirm.objects.create(
                tenant=tenant,
                name=fake.company() + " Law Firm",
                code=f"LF{i}"
            )

            created += 1
            clear_current_tenant()

        self.stdout.write(self.style.SUCCESS(f"🔥 Created {created} law firms."))