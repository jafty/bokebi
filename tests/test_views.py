import pytest
from django.urls import reverse
from django.utils import timezone
from surveys.models import SurveyRecord

@pytest.mark.django_db
def test_home_and_create_pages_render(client):
    assert client.get(reverse("home")).status_code == client.get(reverse("create")).status_code == 200

@pytest.mark.django_db
def test_unknown_survey_is_not_found(client):
    assert client.get(reverse("take-survey", args=["missing"])).status_code == 404


@pytest.mark.django_db
def test_results_share_link_points_to_participation_page(client):
    survey = SurveyRecord.objects.create(
        public_id="team-survey",
        team_name="Team",
        deletion_key_hash="unused",
        created_at=timezone.now(),
    )

    response = client.get(reverse("results", args=[survey.public_id]))

    expected_url = f"http://testserver{reverse('take-survey', args=[survey.public_id])}"
    assert response.status_code == 200
    assert response.context["share_url"] == expected_url
    assert response.content.count(expected_url.encode()) == 2
