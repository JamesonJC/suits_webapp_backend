# apps/lawfirms/management/commands/seed_documents.py

from django.core.management.base import BaseCommand
from faker import Faker

from apps.tenants.models import Tenant
from apps.tenants.context import set_current_tenant, clear_current_tenant
from apps.lawfirms.models import Case, Document


class Command(BaseCommand):
    # ✅ FIX 1: The original file was a bare script — no class, no BaseCommand.
    #           Django's management command discovery requires a class called Command
    #           that extends BaseCommand with a `handle` method.
    #           Without this structure `python manage.py seed_documents` silently fails.

    help = "Seed 3 placeholder documents per case"

    def handle(self, *args, **kwargs):
        fake = Faker()
        created_count = 0

        tenants = Tenant.objects.all()
        if not tenants.exists():
            self.stdout.write(self.style.ERROR("No tenants found. Run seed_tenants first."))
            return

        for tenant in tenants:
            set_current_tenant(tenant)
            cases = Case.objects.all()  # TenantManager scopes this automatically

            for case in cases:
                for j in range(1, 4):  # 3 documents per case
                    Document.objects.create(
                        case=case,
                        # ✅ FIX 2: The original used `title=` and `content=` which
                        #           do not exist on the Document model.
                        #           Document's actual fields are: filename, key, content_type.
                        filename=f"{fake.word()}_{j}.pdf",
                        key=f"tenant_{tenant.id}/case_{case.id}/doc_{j}.pdf",
                        content_type="application/pdf",
                    )
                    created_count += 1

            clear_current_tenant()

        self.stdout.write(
            self.style.SUCCESS(f"Done. Created {created_count} documents total.")
        )