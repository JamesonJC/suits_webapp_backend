from django.contrib import admin

# Register your models here.
from django.contrib import admin
from apps.tenants.models import Tenant


@admin.register(Tenant)
class TenantAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "code", "active")