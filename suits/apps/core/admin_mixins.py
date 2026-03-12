# apps/core/admin_mixins.py
#
# PROBLEM:
#   Every model that extends BaseModel uses TenantManager as its default manager.
#   TenantManager filters to get_current_tenant() from thread-local storage.
#   Django admin sends NO X-Tenant-Code header → get_current_tenant() is None
#   → TenantManager returns qs.none() → list pages empty, all dropdowns empty.
#
# SOLUTION:
#   TenantAdminMixin overrides three methods:
#     get_queryset()           → uses model.unscoped for the list view
#     formfield_for_foreignkey → uses related_model.unscoped for every FK dropdown
#     formfield_for_manytomany → same for M2M fields (Role.permissions, etc.)
#
# USAGE:
#   @admin.register(MyModel)
#   class MyModelAdmin(TenantAdminMixin, admin.ModelAdmin):
#       ...
#
# NOTE: TenantAdminMixin must come BEFORE admin.ModelAdmin in the class definition.

from django.contrib import messages


class TenantAdminMixin:

    def get_queryset(self, request):
        model = self.model
        # BaseModel subclasses have .unscoped; plain models (Document) do not
        if hasattr(model, "unscoped"):
            return model.unscoped.all()
        return model._default_manager.all()

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        """
        Every FK dropdown (law_firm, client, workflow_template, from_step, etc.)
        gets its queryset switched to the unscoped manager.
        """
        related = db_field.related_model
        if hasattr(related, "unscoped"):
            kwargs["queryset"] = related.unscoped.all()
        elif hasattr(related, "_default_manager"):
            kwargs["queryset"] = related._default_manager.all()
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def formfield_for_manytomany(self, db_field, request, **kwargs):
        """Same fix for M2M fields."""
        related = db_field.related_model
        if hasattr(related, "unscoped"):
            kwargs["queryset"] = related.unscoped.all()
        elif hasattr(related, "_default_manager"):
            kwargs["queryset"] = related._default_manager.all()
        return super().formfield_for_manytomany(db_field, request, **kwargs)

    def save_model(self, request, obj, form, change):
        """
        On new records: if tenant wasn't filled in, show a clear error
        instead of letting BaseModel.save() raise a cryptic exception.
        """
        if not change and hasattr(obj, "tenant_id") and not obj.tenant_id:
            self.message_user(
                request,
                "Please select a Tenant before saving.",
                level=messages.ERROR,
            )
            return
        super().save_model(request, obj, form, change)