import pytest
from django.urls import reverse
from surveys.models import SurveyRecord

@pytest.mark.django_db
def test_home_and_create_pages_render(client):
    assert client.get(reverse("home")).status_code == client.get(reverse("create")).status_code == 200

@pytest.mark.django_db
def test_unknown_survey_is_not_found(client):
    assert client.get(reverse("take-survey", args=["missing"])).status_code == 404
