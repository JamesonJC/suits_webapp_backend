from django.contrib import admin
from .models import LawFirm, Attorney, Client, Case, Document

@admin.register(LawFirm)
class LawFirmAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "tenant", "active")
    search_fields = ("name", "code")

@admin.register(Attorney)
class AttorneyAdmin(admin.ModelAdmin):
    list_display = ("user", "law_firm", "title", "active")
    search_fields = ("user__username", "law_firm__name")

@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = ("first_name", "last_name", "email", "law_firm")
    search_fields = ("first_name", "last_name", "email", "law_firm__name")

@admin.register(Case)
class CaseAdmin(admin.ModelAdmin):
    list_display = ("case_number", "title", "law_firm", "client", "status", "start_date", "end_date")
    search_fields = ("case_number", "title", "law_firm__name", "client__first_name", "client__last_name")

@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ("filename", "case", "uploaded_at")
    search_fields = ("filename", "case__case_number", "case__title")