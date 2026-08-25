from datetime import datetime, timezone
import pytest
from domain.entities import ContactRequest, SurveyId
from domain.ports import Clock, ContactRepository, ParticipationRepository, SecretGateway, SurveyRepository, TokenGateway
from domain.use_cases import CreateSurvey, DeleteSurvey, SubmitAnswers, SubmitContactOptIn, ViewSurveyResults

class Surveys(SurveyRepository):
    def __init__(self): self.items = {}
    def add(self, survey): self.items[survey.id] = survey
    def get(self, survey_id): return self.items.get(survey_id)
    def delete(self, survey_id): self.items.pop(survey_id)
class Participations(ParticipationRepository):
    def __init__(self): self.items = []
    def add(self, participation): self.items.append(participation)
    def for_survey(self, survey_id): return [item for item in self.items if item.survey_id == survey_id]
class Contacts(ContactRepository):
    def __init__(self): self.items = []
    def add(self, request): self.items.append(request)
class Tokens(TokenGateway):
    def survey_id(self): return SurveyId("unique")
    def deletion_key(self): return "ONE - TWO - THREE - FOUR"
class Secrets(SecretGateway):
    def encode(self, secret): return f"hash:{secret}"
    def matches(self, secret, encoded): return encoded == self.encode(secret)
class FixedClock(Clock):
    def now(self): return datetime(2026, 1, 1, tzinfo=timezone.utc)

@pytest.fixture
def created():
    repository = Surveys()
    result = CreateSurvey(repository, Tokens(), Secrets(), FixedClock()).execute(" Team ", "secret")
    return repository, result

def test_create_survey_generates_id_key_and_hashes_secrets(created):
    repository, result = created
    assert (result.survey.id, result.survey.team_name, result.deletion_key, result.survey.password_hash) == ("unique", "Team", "ONE - TWO - THREE - FOUR", "hash:secret") and repository.get(result.survey.id) == result.survey

def test_create_survey_allows_no_password():
    result = CreateSurvey(Surveys(), Tokens(), Secrets(), FixedClock()).execute("Team")
    assert result.survey.password_hash is None

def test_create_survey_rejects_blank_name():
    with pytest.raises(ValueError): CreateSurvey(Surveys(), Tokens(), Secrets(), FixedClock()).execute("  ")

def test_submit_answers_stores_one_anonymous_participation(created):
    surveys, result = created; answers = Participations()
    assert SubmitAnswers(surveys, answers).execute(result.survey.id, (1, 2, 3, 4, 5)) == 1 and answers.items[0].answers == (1, 2, 3, 4, 5)

@pytest.mark.parametrize("values", [(1, 2), (0, 2, 3, 4, 5), (1, 2, 3, 4, 6)])
def test_submit_answers_rejects_incomplete_or_out_of_range_values(created, values):
    with pytest.raises(ValueError): SubmitAnswers(created[0], Participations()).execute(created[1].survey.id, values)

def test_submit_answers_rejects_unknown_survey():
    with pytest.raises(LookupError): SubmitAnswers(Surveys(), Participations()).execute(SurveyId("missing"), (1, 2, 3, 4, 5))

def test_contact_opt_in_is_stored_without_survey_or_answer_identifier():
    contacts = Contacts(); SubmitContactOptIn(contacts).execute(" ME@example.org ", True, False, " Team ")
    assert contacts.items == [ContactRequest("me@example.org", True, False, "Team")]

@pytest.mark.parametrize("email,colleagues,organization", [("invalid", True, False), ("me@example.org", False, False)])
def test_contact_opt_in_requires_valid_email_and_a_purpose(email, colleagues, organization):
    with pytest.raises(ValueError): SubmitContactOptIn(Contacts()).execute(email, colleagues, organization, "Team")

def test_results_remain_locked_below_three_participations(created):
    surveys, result = created; answers = Participations(); SubmitAnswers(surveys, answers).execute(result.survey.id, (1, 2, 3, 4, 5))
    assert ViewSurveyResults(surveys, answers).execute(result.survey.id).averages is None

def test_results_unlock_with_averages_at_three_participations(created):
    surveys, result = created; answers = Participations(); use_case = SubmitAnswers(surveys, answers)
    for row in ((1, 2, 3, 4, 5), (3, 2, 3, 2, 1), (5, 2, 3, 3, 3)): use_case.execute(result.survey.id, row)
    assert ViewSurveyResults(surveys, answers).execute(result.survey.id).averages == (3.0, 2.0, 3.0, 3.0, 3.0)

def test_results_reject_unknown_survey():
    with pytest.raises(LookupError): ViewSurveyResults(Surveys(), Participations()).execute(SurveyId("missing"))

def test_delete_survey_accepts_deletion_key(created):
    surveys, result = created; DeleteSurvey(surveys, Secrets()).execute(result.survey.id, result.deletion_key)
    assert surveys.get(result.survey.id) is None

def test_delete_survey_rejects_wrong_key(created):
    with pytest.raises(PermissionError): DeleteSurvey(created[0], Secrets()).execute(created[1].survey.id, "wrong")
