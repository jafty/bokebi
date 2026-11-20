from django.db import transaction

from domain.entities import HelpRequest, HelpStatus, Situation, SurveyId
from .models import HelpRequestRecord


def to_request(row):
    return HelpRequest(
        row.pk.hex, row.email, frozenset(Situation(s) for s in row.situations),
        SurveyId(row.survey_id), row.from_survey, row.created_at, HelpStatus(row.status),
        row.contacted_at, row.closed_at,
    )


class DjangoHelpRepository:
    def get(self, request_id):
        row = HelpRequestRecord.objects.filter(pk=request_id).first()
        return None if row is None else to_request(row)

    def add_once(self, request):
        _, created = HelpRequestRecord.objects.get_or_create(
            pk=request.id,
            defaults={
                "email": request.email,
                "situations": sorted(request.situations),
                "survey_id": request.survey_id,
                "from_survey": request.from_survey,
                "created_at": request.created_at,
                "notification_due_at": request.created_at,
            },
        )
        return created

    @transaction.atomic(using="contacts")
    def transition(self, request_id, status, now):
        row = HelpRequestRecord.objects.select_for_update().get(pk=request_id)
        request = to_request(row).transition(status, now)
        row.status = request.status
        row.contacted_at = request.contacted_at
        row.closed_at = request.closed_at
        if status != HelpStatus.NEW:
            row.notification_due_at = None
        row.save(update_fields=["status", "contacted_at", "closed_at", "notification_due_at"])

    def purge_closed(self, cutoff):
        count, _ = HelpRequestRecord.objects.filter(
            status=HelpStatus.CLOSED, closed_at__lte=cutoff,
        ).delete()
        return count
