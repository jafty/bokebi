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


def test_create_survey_persists_hashed_deletion_key_and_clock(created):
    surveys, result = created
    assert surveys.get(result.survey.id).deletion_key_hash == "hash:ONE - TWO - THREE - FOUR"
    assert result.survey.created_at == datetime(2026, 1, 1, tzinfo=timezone.utc)


@pytest.mark.parametrize("values", [(True, 2, 3, 4, 5), (1.0, 2, 3, 4, 5), (1, 2, 3, 4, 5, 1)])
def test_invalid_answer_types_and_lengths_are_not_saved(created, values):
    answers = Participations()
    with pytest.raises(ValueError):
        SubmitAnswers(created[0], answers).execute(created[1].survey.id, values)
    assert answers.items == []


@pytest.mark.parametrize("colleagues,organization", [(True, False), (False, True), (True, True)])
def test_contact_opt_in_preserves_each_valid_preference(colleagues, organization):
    contacts = Contacts()
    SubmitContactOptIn(contacts).execute("person@example.org", colleagues, organization, "Team")
    assert contacts.items == [ContactRequest("person@example.org", colleagues, organization, "Team")]


def test_contact_opt_in_rejects_blank_group_without_saving():
    contacts = Contacts()
    with pytest.raises(ValueError):
        SubmitContactOptIn(contacts).execute("person@example.org", True, False, "  ")
    assert contacts.items == []


@pytest.mark.parametrize("count", [0, 1, 2])
def test_results_remain_locked_for_each_count_below_threshold(created, count):
    surveys, result = created
    answers = Participations()
    for _ in range(count):
        SubmitAnswers(surveys, answers).execute(result.survey.id, (1, 2, 3, 4, 5))
    results = ViewSurveyResults(surveys, answers).execute(result.survey.id)
    assert (results.participation_count, results.unlocked, results.averages, results.overall_assessment, results.assessments) == (count, False, None, None, ())


@pytest.mark.parametrize("rows,expected", [
    ((2, 2, 3, 2), "negative"),
    ((2, 2, 3, 3), "watch"),
    ((3, 3, 4, 3), "watch"),
    ((3, 3, 4, 4), "positive"),
])
def test_results_assessment_thresholds(created, rows, expected):
    surveys, result = created
    answers = Participations()
    for value in rows:
        SubmitAnswers(surveys, answers).execute(result.survey.id, (value,) * 5)
    results = ViewSurveyResults(surveys, answers).execute(result.survey.id)
    assert results.overall_assessment == expected
    assert results.assessments == (expected,) * 5


def test_delete_missing_survey_raises_lookup_error():
    with pytest.raises(LookupError):
        DeleteSurvey(Surveys(), Secrets()).execute(SurveyId("missing"), "key")


def test_wrong_deletion_key_preserves_survey(created):
    surveys, result = created
    with pytest.raises(PermissionError):
        DeleteSurvey(surveys, Secrets()).execute(result.survey.id, "wrong")
    assert surveys.get(result.survey.id) == result.survey


def test_password_check_accepts_correct_and_rejects_wrong_password(created):
    from domain.use_cases import CheckSurveyPassword
    survey = created[1].survey
    check = CheckSurveyPassword(Secrets())
    assert check.execute(survey, "secret") is True
    assert check.execute(survey, "wrong") is False


def test_password_check_allows_unprotected_survey():
    from domain.use_cases import CheckSurveyPassword
    survey = CreateSurvey(Surveys(), Tokens(), Secrets(), FixedClock()).execute("Team").survey
    assert CheckSurveyPassword(Secrets()).execute(survey, "") is True


def test_domain_errors_provide_their_messages(created):
    surveys, result = created
    answers = Participations()
    cases = [
        (ValueError, "Team name is required", lambda: CreateSurvey(Surveys(), Tokens(), Secrets(), FixedClock()).execute(" ")),
        (LookupError, "Survey not found", lambda: SubmitAnswers(Surveys(), answers).execute(SurveyId("missing"), (1,) * 5)),
        (ValueError, "Every answer must be between 1 and 5", lambda: SubmitAnswers(surveys, answers).execute(result.survey.id, (0,) * 5)),
        (LookupError, "Survey not found", lambda: ViewSurveyResults(Surveys(), answers).execute(SurveyId("missing"))),
        (LookupError, "Survey not found", lambda: DeleteSurvey(Surveys(), Secrets()).execute(SurveyId("missing"), "key")),
        (PermissionError, "Invalid deletion key", lambda: DeleteSurvey(surveys, Secrets()).execute(result.survey.id, "wrong")),
        (ValueError, "A valid email is required", lambda: SubmitContactOptIn(Contacts()).execute("bad", True, False, "Team")),
        (ValueError, "At least one contact option is required", lambda: SubmitContactOptIn(Contacts()).execute("a@b", False, False, "Team")),
        (ValueError, "A group label is required", lambda: SubmitContactOptIn(Contacts()).execute("a@b", True, False, " ")),
    ]
    for error_type, message, action in cases:
        with pytest.raises(error_type) as error:
            action()
        assert str(error.value) == message


def test_unlocked_results_include_count_and_round_averages(created):
    surveys, result = created
    answers = Participations()
    for value in (1, 1, 2):
        SubmitAnswers(surveys, answers).execute(result.survey.id, (value,) * 5)
    results = ViewSurveyResults(surveys, answers).execute(result.survey.id)
    assert results.unlocked is True
    assert results.participation_count == 3
    assert results.averages == (1.33,) * 5


def test_overall_average_rounds_to_two_decimal_places(created):
    surveys, result = created
    answers = Participations()
    for row in ((2, 1, 1, 1, 1), (1, 1, 1, 1, 1), (1, 1, 1, 1, 1)):
        SubmitAnswers(surveys, answers).execute(result.survey.id, row)
    assert ViewSurveyResults(surveys, answers).execute(result.survey.id).overall_average == 1.07
