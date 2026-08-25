from domain.entities import Participation, Survey, SurveyId
from domain.ports import ParticipationRepository, SurveyRepository
from .models import ParticipationRecord, SurveyRecord

class DjangoSurveyRepository(SurveyRepository):
    def add(self, survey):
        SurveyRecord.objects.create(public_id=survey.id, team_name=survey.team_name, deletion_key_hash=survey.deletion_key_hash, password_hash=survey.password_hash, created_at=survey.created_at)
    def get(self, survey_id):
        row = SurveyRecord.objects.filter(public_id=survey_id).first()
        return None if row is None else Survey(SurveyId(row.public_id), row.team_name, row.deletion_key_hash, row.password_hash, row.created_at)
    def delete(self, survey_id): SurveyRecord.objects.filter(public_id=survey_id).delete()

class DjangoParticipationRepository(ParticipationRepository):
    def add(self, participation):
        survey = SurveyRecord.objects.get(public_id=participation.survey_id)
        _, created = ParticipationRecord.objects.get_or_create(
            survey=survey,
            submission_token=participation.submission_token,
            defaults={"answers": list(participation.answers)},
        )
        return created
    def for_survey(self, survey_id):
        return [Participation(SurveyId(survey_id), tuple(row.answers), row.submission_token) for row in ParticipationRecord.objects.filter(survey__public_id=survey_id)]
