from django.contrib import admin
from django.utils import timezone

from .models import ContactRequestRecord


@admin.action(description="Marquer les demandes sélectionnées comme contactées")
def mark_as_contacted(modeladmin, request, queryset):
    queryset.filter(contacted_at__isnull=True).update(contacted_at=timezone.now())


@admin.action(description="Marquer les demandes sélectionnées comme à traiter")
def mark_as_pending(modeladmin, request, queryset):
    queryset.update(contacted_at=None)


@admin.register(ContactRequestRecord)
class ContactRequestAdmin(admin.ModelAdmin):
    list_display = (
        "email",
        "group_label",
        "wants_colleagues",
        "wants_organization",
        "created_at",
        "contacted_at",
    )
    list_filter = ("group_label", "wants_colleagues", "wants_organization", "contacted_at")
    search_fields = ("email", "group_label")
    readonly_fields = ("email", "group_label", "wants_colleagues", "wants_organization", "created_at")
    actions = (mark_as_contacted, mark_as_pending)
    date_hierarchy = "created_at"

    def has_add_permission(self, request):
        return False
