from django.contrib import admin, messages
from django.urls import reverse
from django.utils import timezone
from django.utils.html import format_html

from domain.entities import HelpStatus
from domain.use_cases import MaintainHelpRequests
from surveys.forms import SITUATIONS
from surveys.gateways import SystemClock
from surveys.repositories import DjangoSurveyRepository
from .models import HelpRequestRecord
from .repositories import DjangoHelpRepository, to_request

@admin.register(HelpRequestRecord)
class HelpRequestAdmin(admin.ModelAdmin):
    fields = (
        "email", "submitted_situations", "origin", "group", "created_at", "response_deadline",
        "status", "contacted_at", "closed_at",
    )
    readonly_fields = fields
    list_display = ("email", "origin", "group", "status", "created_at", "response_deadline")
    list_filter = ("status", "from_survey")
    search_fields = ("=survey_id",)
    actions = ("mark_contacted", "mark_in_progress", "mark_closed")

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    @admin.display(description="Situations transmises")
    def submitted_situations(self, obj):
        return " / ".join(SITUATIONS[s] for s in obj.situations) or "Aucune sélection"

    @admin.display(description="Origine")
    def origin(self, obj):
        return "Depuis un sondage" if obj.from_survey else "Demande initiale"

    @admin.display(description="Sondage")
    def group(self, obj):
        survey = DjangoSurveyRepository().get(obj.survey_id)
        if survey is None and not obj.from_survey:
            return "Aucun sondage actif"
        queue = reverse("admin:contacts_helprequestrecord_changelist")
        label = "Sondage supprimé" if survey is None else f"{survey.name} ({survey.response_count} réponses)"
        return format_html('<a href="{}?survey_id__exact={}">{}</a>', queue, obj.survey_id, label)

    @admin.display(description="Première réponse avant", ordering="created_at")
    def response_deadline(self, obj):
        deadline = to_request(obj).deadline
        formatted = timezone.localtime(deadline).strftime("%d/%m/%Y %H:%M")
        if obj.status == HelpStatus.NEW and deadline < timezone.now():
            return f"{formatted} (en retard)"
        return formatted

    def _advance(self, request, queryset, status):
        maintain = MaintainHelpRequests(DjangoHelpRepository(), SystemClock())
        invalid = 0
        for request_id in queryset.values_list("pk", flat=True):
            try:
                maintain.transition(request_id, status)
            except (ValueError, HelpRequestRecord.DoesNotExist):
                invalid += 1
        if invalid:
            self.message_user(request, f"{invalid} demande(s) sans changement de statut.", messages.WARNING)

    @admin.action(permissions=["change"], description="Marquer comme contacté")
    def mark_contacted(self, request, queryset):
        self._advance(request, queryset, HelpStatus.CONTACTED)

    @admin.action(permissions=["change"], description="Marquer comme en cours")
    def mark_in_progress(self, request, queryset):
        self._advance(request, queryset, HelpStatus.IN_PROGRESS)

    @admin.action(permissions=["change"], description="Clore les demandes")
    def mark_closed(self, request, queryset):
        self._advance(request, queryset, HelpStatus.CLOSED)
