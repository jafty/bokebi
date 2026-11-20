from django.db import transaction

from domain.entities import Survey, SurveyId
from .models import SurveyCreationReceipt, VoteReceipt, WorkplaceSurveyRecord


def to_survey(row):
    return Survey(
        SurveyId(row.public_id), row.name, row.deletion_key_hash, row.password_hash,
        row.created_at, row.response_count, tuple(row.counts),
    )


class DjangoSurveyRepository:
    def get(self, survey_id):
        row = WorkplaceSurveyRecord.objects.filter(public_id=survey_id).first()
        return None if row is None else to_survey(row)

    @transaction.atomic
    def create_once(self, survey, creator_receipt):
        _, created = SurveyCreationReceipt.objects.get_or_create(
            public_id=survey.id, defaults={"created_at": survey.created_at},
        )
        if not created:
            return self.get(survey.id)
        row = WorkplaceSurveyRecord.objects.create(
            public_id=survey.id, name=survey.name, deletion_key_hash=survey.deletion_key_hash,
            password_hash=survey.password_hash, created_at=survey.created_at,
            response_count=survey.response_count, counts=list(survey.counts),
        )
        if creator_receipt is not None:
            VoteReceipt.objects.create(survey=row, digest=creator_receipt)
        return survey

    @transaction.atomic
    def add_ballot(self, survey_id, receipt, ballot):
        row = WorkplaceSurveyRecord.objects.select_for_update().filter(public_id=survey_id).first()
        if row is None:
            raise LookupError("Sondage introuvable.")
        _, created = VoteReceipt.objects.get_or_create(survey=row, digest=receipt)
        if created:
            survey = to_survey(row).count(ballot)
            row.response_count = survey.response_count
            row.counts = list(survey.counts)
            row.save(update_fields=["response_count", "counts"])
        return created

    @transaction.atomic
    def delete(self, survey_id):
        rows = WorkplaceSurveyRecord.objects.select_for_update().filter(public_id=survey_id)
        for row in rows:
            row.delete()
