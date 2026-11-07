from dataclasses import dataclass
from .entities import ContactRequest, Participation, STANDARD_QUESTIONS, Survey, SurveyId
from .ports import Clock, ContactRepository, ParticipationRepository, SecretGateway, SurveyRepository, TokenGateway

MINIMUM_PARTICIPATIONS = 3

@dataclass(frozen=True)
class CreatedSurvey:
    survey: Survey
    deletion_key: str

class CreateSurvey:
    def __init__(self, surveys: SurveyRepository, tokens: TokenGateway, secrets: SecretGateway, clock: Clock):
        self.surveys, self.tokens, self.secrets, self.clock = surveys, tokens, secrets, clock
    def execute(self, team_name: str, password: str | None = None) -> CreatedSurvey:
        name = team_name.strip()
        if not name:
            raise ValueError("Team name is required")
        key = self.tokens.deletion_key()
        survey = Survey(self.tokens.survey_id(), name, self.secrets.encode(key), self.secrets.encode(password) if password else None, self.clock.now())
        self.surveys.add(survey)
        return CreatedSurvey(survey, key)

class SubmitAnswers:
    def __init__(self, surveys: SurveyRepository, participations: ParticipationRepository):
        self.surveys, self.participations = surveys, participations
    def execute(self, survey_id: SurveyId, answers: tuple[int, ...]) -> int:
        if self.surveys.get(survey_id) is None:
            raise LookupError("Survey not found")
        if len(answers) != len(STANDARD_QUESTIONS) or any(type(answer) is not int or answer not in range(1, 6) for answer in answers):
            raise ValueError("Every answer must be between 1 and 5")
        self.participations.add(Participation(survey_id, answers))
        return len(self.participations.for_survey(survey_id))

class CheckSurveyPassword:
    def __init__(self, secrets: SecretGateway):
        self.secrets = secrets

    def execute(self, survey: Survey, password: str) -> bool:
        return survey.password_hash is None or self.secrets.matches(password, survey.password_hash)

class SubmitContactOptIn:
    def __init__(self, contacts: ContactRepository): self.contacts = contacts
    def execute(self, email: str, wants_colleagues: bool, wants_organization: bool, group_label: str) -> None:
        self.contacts.add(ContactRequest(email.strip().lower(), wants_colleagues, wants_organization, group_label.strip()))

@dataclass(frozen=True)
class SurveyResults:
    participation_count: int
    averages: tuple[float, ...] | None
    @property
    def unlocked(self) -> bool: return results_unlocked(self.averages)

    @property
    def overall_average(self) -> float | None:
        return calculate_overall_average(self.averages)

    @property
    def overall_assessment(self) -> str | None:
        return assess_overall(self.overall_average)

    @property
    def assessments(self) -> tuple[str, ...]:
        return assess_averages(self.averages)


def results_unlocked(averages: tuple[float, ...] | None) -> bool:
    return averages is not None


def calculate_overall_average(averages: tuple[float, ...] | None) -> float | None:
    return round(sum(averages) / len(averages), 2) if averages else None


def assess_overall(average: float | None) -> str | None:
    return assess_average(average) if average is not None else None


def assess_averages(averages: tuple[float, ...] | None) -> tuple[str, ...]:
    return tuple(assess_average(average) for average in averages or ())


def assess_average(average: float) -> str:
    if average < 2.5:
        return "negative"
    if average < 3.5:
        return "watch"
    return "positive"

class ViewSurveyResults:
    def __init__(self, surveys: SurveyRepository, participations: ParticipationRepository):
        self.surveys, self.participations = surveys, participations
    def execute(self, survey_id: SurveyId) -> SurveyResults:
        if self.surveys.get(survey_id) is None: raise LookupError("Survey not found")
        rows = self.participations.for_survey(survey_id)
        if len(rows) < MINIMUM_PARTICIPATIONS: return SurveyResults(len(rows), None)
        return SurveyResults(len(rows), tuple(round(sum(row.answers[i] for row in rows) / len(rows), 2) for i in range(len(STANDARD_QUESTIONS))))

class DeleteSurvey:
    def __init__(self, surveys: SurveyRepository, secrets: SecretGateway): self.surveys, self.secrets = surveys, secrets
    def execute(self, survey_id: SurveyId, deletion_key: str) -> None:
        survey = self.surveys.get(survey_id)
        if survey is None: raise LookupError("Survey not found")
        if not self.secrets.matches(deletion_key, survey.deletion_key_hash): raise PermissionError("Invalid deletion key")
        self.surveys.delete(survey_id)
