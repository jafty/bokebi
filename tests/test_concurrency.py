from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import pytest
from django.db import connection, connections

from domain.entities import Ballot, Situation, Survey, SurveyId
from surveys.gateways import SystemClock
from surveys.repositories import DjangoSurveyRepository


@pytest.mark.django_db(transaction=True)
def test_postgresql_serializes_ballots_and_deduplicates_same_receipt():
    if connection.vendor != "postgresql":
        pytest.skip("Exige PostgreSQL pour vérifier les verrous de ligne.")
    repo = DjangoSurveyRepository()
    survey_id = SurveyId("parallel")
    repo.create_once(Survey(survey_id, "Équipe", "hash", None, SystemClock().now()), None)
    barrier = Barrier(4)

    def vote(receipt):
        try:
            barrier.wait(timeout=10)
            return repo.add_ballot(survey_id, receipt, Ballot(frozenset({Situation.OVERTIME})))
        finally:
            connections.close_all()

    with ThreadPoolExecutor(max_workers=4) as pool:
        outcomes = list(pool.map(vote, ["same", "same", "other", "last"]))
    assert sum(outcomes) == 3
    assert repo.get(survey_id).response_count == 3
    assert repo.get(survey_id).results == (3, 0, 0, 0, 0)
