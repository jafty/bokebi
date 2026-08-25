import pytest
from django.urls import reverse
from surveys.models import SurveyRecord

@pytest.mark.django_db
def test_home_and_create_pages_render(client):
    assert client.get(reverse("home")).status_code == client.get(reverse("create")).status_code == 200

@pytest.mark.django_db
def test_unknown_survey_is_not_found(client):
    assert client.get(reverse("take-survey", args=["missing"])).status_code == 404

@pytest.mark.django_db
def test_repeated_posts_from_one_browser_count_once(client):
    from datetime import datetime, timezone

    survey = SurveyRecord.objects.create(
        public_id="repeat-test",
        team_name="Team",
        deletion_key_hash="hash",
        created_at=datetime.now(timezone.utc),
    )
    url = reverse("take-survey", args=[survey.public_id])
    client.get(url)
    answers = {f"q{i}": "3" for i in range(1, 6)}
    assert client.post(url, answers).status_code == 200
    assert client.post(url, answers).status_code == 200
    assert survey.participations.count() == 1
