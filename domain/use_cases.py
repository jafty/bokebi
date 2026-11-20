from collections.abc import Collection

from .entities import CLOSED_RETENTION, Ballot, HelpRequest, HelpStatus, Situation, Survey, SurveyId
from .ports import Clock, HelpNotificationGateway, HelpRepository, SecretGateway, SurveyRepository


class RequestHelp:
    def __init__(self, requests: HelpRepository, clock: Clock, notifications: HelpNotificationGateway):
        self.requests = requests
        self.clock = clock
        self.notifications = notifications

    def execute(
        self, request_id: str, email: str, situations: Collection[Situation],
        survey_id: SurveyId, *, from_survey: bool,
    ) -> bool:
        email = email.strip()
        if not email or "@" not in email:
            raise ValueError("Saisis une adresse e-mail valide.")
        request = HelpRequest(
            request_id, email, frozenset(situations), survey_id, from_survey, self.clock.now(),
        )
        created = self.requests.add_once(request)
        if created:
            self.notifications.request_received(request.id)
        return created


class CreateSurvey:
    def __init__(self, surveys: SurveyRepository, secrets: SecretGateway, clock: Clock):
        self.surveys = surveys
        self.secrets = secrets
        self.clock = clock

    def execute(
        self, request: HelpRequest, name: str, password: str, deletion_key: str,
        *, include_situations: bool, receipt: str,
    ) -> Survey | None:
        if request.from_survey:
            raise PermissionError("Cette demande ne permet pas de créer un sondage.")
        survey = Survey(
            request.survey_id, name.strip() or "Votre équipe", self.secrets.encode(deletion_key),
            self.secrets.encode(password) if password else None, self.clock.now(),
        )
        if include_situations and request.situations:
            return self.surveys.create_once(survey.count(Ballot(request.situations)), receipt)
        return self.surveys.create_once(survey, None)


class DeleteSurvey:
    def __init__(self, surveys: SurveyRepository, secrets: SecretGateway):
        self.surveys = surveys
        self.secrets = secrets

    def execute(self, survey: Survey, deletion_key: str) -> None:
        if not self.secrets.matches(deletion_key, survey.deletion_key_hash):
            raise PermissionError("Clé de suppression incorrecte.")
        self.surveys.delete(survey.id)


class MaintainHelpRequests:
    def __init__(self, requests: HelpRepository, clock: Clock):
        self.requests = requests
        self.clock = clock

    def transition(self, request_id: str, status: HelpStatus) -> None:
        self.requests.transition(request_id, status, self.clock.now())

    def purge(self) -> int:
        return self.requests.purge_closed(self.clock.now() - CLOSED_RETENTION)
