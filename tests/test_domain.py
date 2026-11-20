from dataclasses import replace
from datetime import datetime, timedelta, timezone

import pytest

from domain.entities import Ballot, HelpRequest, HelpStatus, Situation, Survey, SurveyId
from domain.use_cases import CreateSurvey, DeleteSurvey, MaintainHelpRequests, RequestHelp

NOW = datetime(2026, 11, 20, tzinfo=timezone.utc)
SURVEY_ID = SurveyId("poll-id")


class FixedClock:
    def now(self):
        return NOW


class MemoryHelpRequests:
    def __init__(self):
        self.requests = {}

    def add_once(self, request):
        if request.id in self.requests:
            return False
        self.requests[request.id] = request
        return True

    def transition(self, request_id, status, now):
        self.requests[request_id] = self.requests[request_id].transition(status, now)

    def purge_closed(self, cutoff):
        eligible = [
            request.id for request in self.requests.values()
            if request.closed_at is not None and request.closed_at <= cutoff
        ]
        for request_id in eligible:
            del self.requests[request_id]
        return len(eligible)


class MemoryNotifications:
    def __init__(self):
        self.received = []

    def request_received(self, request_id):
        self.received.append(request_id)


class MemorySurveys:
    def __init__(self):
        self.surveys = {}
        self.receipts = {}

    def create_once(self, survey, creator_receipt):
        if survey.id not in self.receipts:
            self.surveys[survey.id] = survey
            self.receipts[survey.id] = creator_receipt
        return self.surveys.get(survey.id)

    def delete(self, survey_id):
        del self.surveys[survey_id]


class TestSecrets:
    __test__ = False

    def encode(self, value):
        return "hash:" + value

    def matches(self, value, encoded):
        return self.encode(value) == encoded


@pytest.fixture
def request_record():
    return HelpRequest("request-id", "person@example.com", frozenset({Situation.PAY}), SURVEY_ID, False, NOW)


def test_help_request_allows_no_situations_and_is_replayed():
    requests = MemoryHelpRequests()
    notifications = MemoryNotifications()
    submit = RequestHelp(requests, FixedClock(), notifications)
    assert submit.execute("one", " person@example.com ", (), SURVEY_ID, from_survey=False)
    assert not submit.execute("one", "second@example.com", (), SURVEY_ID, from_survey=False)
    assert requests.requests["one"].email == "person@example.com"
    assert not requests.requests["one"].situations
    assert notifications.received == ["one"]


@pytest.mark.parametrize("email", [" ", "invalid"])
def test_help_request_validates_email(email):
    with pytest.raises(ValueError):
        RequestHelp(MemoryHelpRequests(), FixedClock(), MemoryNotifications()).execute("one", email, (), SURVEY_ID, from_survey=False)


def test_help_request_deadline_and_transitions(request_record):
    assert request_record.deadline == NOW + timedelta(hours=24)
    with pytest.raises(ValueError):
        request_record.transition(HelpStatus.IN_PROGRESS, NOW)
    contacted = request_record.transition(HelpStatus.CONTACTED, NOW)
    assert contacted.transition(HelpStatus.CONTACTED, NOW + timedelta(hours=1)) is contacted
    active = contacted.transition(HelpStatus.IN_PROGRESS, NOW)
    closed = active.transition(HelpStatus.CLOSED, NOW + timedelta(hours=24))
    assert closed.contacted_at == NOW
    assert closed.closed_at == NOW + timedelta(hours=24)
    with pytest.raises(ValueError):
        closed.transition(HelpStatus.NEW, NOW)


def test_retention_includes_cutoff_and_only_closed(request_record):
    repo = MemoryHelpRequests()
    repo.add_once(request_record)
    closed_at = NOW - timedelta(days=30)
    repo.add_once(replace(request_record, id="expired").transition(HelpStatus.CLOSED, closed_at))
    repo.add_once(replace(request_record, id="just-closed").transition(HelpStatus.CLOSED, closed_at + timedelta(seconds=1)))
    use_case = MaintainHelpRequests(repo, FixedClock())
    assert use_case.purge() == 1
    use_case.transition(request_record.id, HelpStatus.CONTACTED)
    assert repo.requests[request_record.id].contacted_at == NOW
    assert "just-closed" in repo.requests


@pytest.mark.parametrize("situations, none_applies", [(frozenset(), False), (frozenset({Situation.PAY}), True)])
def test_ballot_requires_choices_or_exclusive_none(situations, none_applies):
    with pytest.raises(ValueError):
        Ballot(situations, none_applies)


def test_results_follow_total_and_counts_are_independent():
    poll = Survey(SURVEY_ID, "Dépôt", "hash", None, NOW)
    selected = Ballot(frozenset({Situation.PAY, Situation.PRESSURE}))
    assert poll.results is None
    assert poll.count(selected).results is None
    two = poll.count(selected).count(Ballot(frozenset(), True))
    assert two.results is None
    three = two.count(selected)
    assert three.results == (0, 0, 2, 0, 2)
    assert three.count(selected).results == (0, 0, 3, 0, 3)


def test_survey_defaults_and_explicit_first_vote(request_record):
    repo = MemorySurveys()
    create = CreateSurvey(repo, TestSecrets(), FixedClock())
    poll = create.execute(request_record, " ", "", "delete", include_situations=False, receipt="vote")
    assert (poll.name, poll.password_hash, poll.response_count) == ("Votre équipe", None, 0)
    assert repo.receipts[poll.id] is None
    assert create.execute(request_record, "Other", "", "delete", include_situations=True, receipt="vote") == poll
    seeded = create.execute(
        replace(request_record, survey_id=SurveyId("second")), " Dépôt ", "open", "delete",
        include_situations=True, receipt="vote",
    )
    assert (seeded.name, seeded.password_hash, seeded.response_count) == ("Dépôt", "hash:open", 1)
    assert repo.receipts[seeded.id] == "vote"


def test_survey_rejects_colleague_and_never_seeds_empty_request(request_record):
    create = CreateSurvey(MemorySurveys(), TestSecrets(), FixedClock())
    with pytest.raises(PermissionError):
        create.execute(replace(request_record, from_survey=True), "", "", "d", include_situations=True, receipt="v")
    poll = create.execute(replace(request_record, situations=frozenset()), "", "", "d", include_situations=True, receipt="v")
    assert poll.response_count == 0


def test_only_key_holder_can_delete_survey_and_replay_does_not_recreate(request_record):
    repo = MemorySurveys()
    create = CreateSurvey(repo, TestSecrets(), FixedClock())
    poll = create.execute(request_record, "", "", "key", include_situations=False, receipt="v")
    delete = DeleteSurvey(repo, TestSecrets())
    with pytest.raises(PermissionError):
        delete.execute(poll, "wrong")
    delete.execute(poll, "key")
    assert create.execute(request_record, "", "", "key", include_situations=False, receipt="v") is None


def test_situation_codes_must_be_known(request_record):
    with pytest.raises(ValueError, match="Situation inconnue"):
        Ballot(frozenset({"unknown"}))
    with pytest.raises(ValueError, match="Situation inconnue"):
        replace(request_record, situations=frozenset({"unknown"}))
