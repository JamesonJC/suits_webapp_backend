from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from faker import Faker
import random

from apps.tenants.models import Tenant
from apps.tenants.context import set_current_tenant, clear_current_tenant
from apps.lawfirms.models import LawFirm, Attorney


class Command(BaseCommand):
    help = "Flush tenants, create tenants with law firms, and seed attorneys"

    def handle(self, *args, **kwargs):
        fake = Faker()
        User = get_user_model()

        # --- Step 1: Flush existing data ---
        self.stdout.write("⚠️  Deleting existing Attorneys, Law Firms, and Tenants...")
        Attorney.objects.all().delete()
        LawFirm.objects.all().delete()
        Tenant.objects.all().delete()
        self.stdout.write(self.style.SUCCESS("✅ Flushed existing data."))

        # --- Step 2: Create tenants and law firms ---
        self.stdout.write("🌱 Creating tenants and law firms...")
        tenants = []
        for i in range(5):
            tenant = Tenant.objects.create(
                name=fake.company() + " Tenant",
                code=f"T{i+1}"
            )
            tenants.append(tenant)

            set_current_tenant(tenant)
            LawFirm.objects.create(
                tenant=tenant,
                name=fake.company() + " Law Firm",
                code=f"LF{i+1}"
            )
            clear_current_tenant()
            self.stdout.write(
                self.style.SUCCESS(f"✅ Created Tenant & Law Firm: {tenant.name}")
            )

        # --- Step 3: Seed 100 attorneys randomly ---
        self.stdout.write("🌱 Creating 100 random attorneys...")
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