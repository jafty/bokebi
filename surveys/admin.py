from django.contrib import admin

from .forms import SITUATIONS
from .models import WorkplaceSurveyRecord
from .repositories import to_survey


@admin.register(WorkplaceSurveyRecord)
class WorkplaceSurveyAdmin(admin.ModelAdmin):
    list_display = ("name", "public_id", "created_at", "response_count")
    search_fields = ("name", "=public_id")
    fields = (*list_display, "aggregate_results")
    readonly_fields = fields

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    @admin.display(description="Résultats agrégés")
    def aggregate_results(self, obj):
        counts = to_survey(obj).results
        if counts is None:
            return "Disponibles à partir de trois réponses."
        return " / ".join(
            f"{label} {count} sur {obj.response_count}"
            for label, count in zip(SITUATIONS.values(), counts, strict=True)
        )
