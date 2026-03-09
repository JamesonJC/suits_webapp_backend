# apps/core/admin_mixins.py
#
# WHY THIS EXISTS:
# All our models use TenantManager which filters queries to the current tenant.
# In Django admin, there is no X-Tenant-Code header, so get_current_tenant()
# returns None and TenantManager returns .none() — meaning all dropdowns are empty.
#
# TenantAdminMixin solves this by:
#   1. Using model.unscoped (bypasses tenant filter) for the main list queryset
#   2. Overriding formfield_for_foreignkey so every FK dropdown uses unscoped too

from django.contrib import admin
from django.contrib import messages


class TenantAdminMixin:
    """
    Mix this into any ModelAdmin where the model uses BaseModel (TenantManager).
    It bypasses tenant filtering so admin users can see and edit all data.
    """

    def get_queryset(self, request):
        """
        Use the unscoped manager so all rows appear regardless of tenant context.
        Falls back to default manager for models that don't have unscoped (e.g. Document).
        """
        model = self.model
        if hasattr(model, "unscoped"):
            return model.unscoped.all()
        return model._default_manager.all()

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        """
        For every FK on a form (dropdowns), force the queryset to use
        the unscoped manager so all options are visible.

        Example: on the Case form, law_firm, client, and workflow_template
        were all showing empty because TenantManager filtered them to nothing.
        """
        related_model = db_field.related_model

        if hasattr(related_model, "unscoped"):
            # Use unscoped — bypass tenant filtering for admin dropdowns
            kwargs["queryset"] = related_model.unscoped.all()
        elif hasattr(related_model, "_default_manager"):
            kwargs["queryset"] = related_model._default_manager.all()

        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def formfield_for_manytomany(self, db_field, request, **kwargs):
        """Same fix for ManyToMany fields (e.g. permissions on roles)."""
        related_model = db_field.related_model

        if hasattr(related_model, "unscoped"):
            kwargs["queryset"] = related_model.unscoped.all()

        return super().formfield_for_manytomany(db_field, request, **kwargs)

    def save_model(self, request, obj, form, change):
        """
        If the object doesn't have a tenant yet (new object), we cannot
        auto-assign it because admin has no tenant context. Raise a clear error
        instead of a cryptic 'Tenant context missing' exception.
        """
        if not change and hasattr(obj, "tenant_id") and not obj.tenant_id:
            self.message_user(
                request,
                "You must select a Tenant before saving.",
                level=messages.ERROR,
            )
            return

        # Bypass BaseModel.save()'s tenant auto-assign check by setting
        # tenant directly from the form field before save
        super().save_model(request, obj, form, change)