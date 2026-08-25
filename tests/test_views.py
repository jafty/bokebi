import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password
from django.urls import reverse
from surveys.models import ParticipationRecord, SurveyRecord
from contacts.models import ContactRequestRecord

@pytest.mark.django_db
def test_home_and_create_pages_render(client):
    home = client.get(reverse("home"))
    assert home.status_code == client.get(reverse("create")).status_code == 200
    assert home.content.decode().count("Créer un sondage maintenant") == 2

@pytest.mark.django_db
def test_unknown_survey_is_not_found(client):
    assert client.get(reverse("take-survey", args=["missing"])).status_code == 404

@pytest.fixture
def protected_survey():
    return SurveyRecord.objects.create(
        public_id="protected",
        team_name="Protected team",
        deletion_key_hash=make_password("delete me"),
        password_hash=make_password("open sesame"),
        created_at="2026-01-01T00:00:00Z",
    )

@pytest.mark.django_db
@pytest.mark.parametrize("route_name", ["take-survey", "results"])
def test_protected_survey_requires_password(client, protected_survey, route_name):
    url = reverse(route_name, args=[protected_survey.public_id])

    assert client.get(url).status_code == 403
    response = client.post(url, {"survey_password": "wrong"})
    assert response.status_code == 403
    assert "Mot de passe incorrect" in response.content.decode()

    response = client.post(url, {"survey_password": "open sesame"})
    assert response.status_code == 302
    assert response.url == url
    assert client.get(url).status_code == 200

@pytest.mark.django_db
def test_protected_survey_rejects_answer_submission_without_password(client, protected_survey):
    url = reverse("take-survey", args=[protected_survey.public_id])

    assert client.post(url, {"q1": "5"}).status_code == 403
    assert ParticipationRecord.objects.count() == 0


@pytest.mark.django_db
def test_multiple_submissions_create_distinct_participation_records(client):
    survey = SurveyRecord.objects.create(
        public_id="repeatable",
        team_name="Repeatable survey",
        deletion_key_hash=make_password("delete me"),
        created_at="2026-01-01T00:00:00Z",
    )
    url = reverse("take-survey", args=[survey.public_id])

    first_answers = {f"q{i}": str(i) for i in range(1, 6)}
    second_answers = {f"q{i}": str(6 - i) for i in range(1, 6)}

    assert client.post(url, first_answers).status_code == 200
    assert client.post(url, second_answers).status_code == 200
    assert list(
        ParticipationRecord.objects.filter(survey=survey)
        .order_by("id")
        .values_list("answers", flat=True)
    ) == [[1, 2, 3, 4, 5], [5, 4, 3, 2, 1]]


@pytest.mark.django_db
@pytest.mark.parametrize("page", ["legal", "privacy", "ethics", "contact"])
def test_footer_information_pages_render(client, page):
    assert client.get(reverse("information-page", args=[page])).status_code == 200


@pytest.mark.django_db
def test_results_invite_uses_poll_url_and_unlocked_results_have_analysis(client):
    survey = SurveyRecord.objects.create(public_id="results", team_name="Results", deletion_key_hash=make_password("delete"), created_at="2026-01-01T00:00:00Z")
    for answers in ([1, 1, 1, 1, 1], [2, 2, 2, 2, 2], [3, 3, 3, 3, 3]):
        ParticipationRecord.objects.create(survey=survey, answers=answers)

    response = client.get(reverse("results", args=[survey.public_id]))
    content = response.content.decode()
    assert response.status_code == 200
    assert f'/s/{survey.public_id}/"' in content
    assert "Analyse des résultats" in content
    assert "Situation préoccupante" in content


@pytest.mark.django_db(databases=["default", "contacts"])
def test_contact_requests_are_available_only_in_authenticated_admin(client):
    request = ContactRequestRecord.objects.create(
        email="person@example.com",
        group_label="Example team",
        wants_colleagues=True,
        wants_organization=False,
    )
    url = reverse("admin:contacts_contactrequestrecord_changelist")

    response = client.get(url)
    assert response.status_code == 302
    assert response.url.startswith(reverse("admin:login"))

    admin = get_user_model().objects.create_superuser(username="operator", password="safe-password")
    client.force_login(admin)
    response = client.get(url)
    assert response.status_code == 200
    assert request.email in response.content.decode()
    assert request.group_label in response.content.decode()


@pytest.mark.django_db(databases=["default", "contacts"])
def test_contact_opt_in_stores_group_label_but_no_survey_identifier(client):
    survey = SurveyRecord.objects.create(
        public_id="private-survey-id",
        team_name="Example company",
        deletion_key_hash=make_password("delete"),
        created_at="2026-01-01T00:00:00Z",
    )

    response = client.post(reverse("contact-opt-in", args=[survey.public_id]), {
        "email": "person@example.com",
        "wants_colleagues": "on",
    })

    assert response.status_code == 302
    contact = ContactRequestRecord.objects.get()
    assert contact.group_label == "Example company"
    assert not hasattr(contact, "survey_id")
