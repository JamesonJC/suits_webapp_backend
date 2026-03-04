from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from faker import Faker
import random

from apps.tenants.models import Tenant
from apps.tenants.context import set_current_tenant, clear_current_tenant
from apps.lawfirms.models import LawFirm, Attorney


class Command(BaseCommand):
    help = "Seed 100 random attorneys across tenants and law firms"

    def handle(self, *args, **kwargs):
        fake = Faker()
        User = get_user_model()
        tenants = Tenant.objects.all()

        if not tenants.exists():
            self.stdout.write(self.style.ERROR("No tenants found."))
            return

        created_count = 0

        for _ in range(100):
            tenant = random.choice(tenants)
            set_current_tenant(tenant)

            law_firms = LawFirm.objects.all()
            if not law_firms.exists():
                clear_current_tenant()
                continue

            firm = random.choice(law_firms)

            user = User.objects.create_user(
                username=fake.user_name() + str(random.randint(1, 9999)),
                email=fake.email(),
                password="password"
            )

            Attorney.objects.create(
                user=user,
                law_firm=firm,
                title=random.choice(["Partner", "Associate"])
            )

            created_count += 1

            clear_current_tenant()

        self.stdout.write(
            self.style.SUCCESS(f"🔥 Successfully created {created_count} attorneys.")
        )