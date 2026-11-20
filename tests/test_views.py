import re
from datetime import timedelta
from urllib.parse import parse_qs, urlparse

import pytest
from django.test import Client
from django.urls import reverse
from django.utils import timezone

from contacts.models import HelpRequestRecord
from domain.entities import Situation
from surveys.models import VoteReceipt, WorkplaceSurveyRecord
from surveys.repositories import DjangoSurveyRepository

pytestmark = pytest.mark.django_db(databases=["default", "contacts"])
EMAIL = "private@example.com"


def token(client, route):
    response = client.get(route)
    return re.search(rb'name="flow" value="([^"]+)"', response.content)[1].decode()


def ask(client, route="/aide/", email=EMAIL, **fields):
    return client.post(route, {"email": email, "flow": token(client, route), **fields})


def prepare(client, **fields):
    response = ask(client, **fields)
    return response.url.replace("/confirmation/", "/partage/")


def create(client, *, password="", seed=False):
    preparation = prepare(client, situations=[Situation.PAY])
    response = client.post(preparation, {"name": "Dépôt Sud", "password": password, "include_situations": seed})
    assert response.status_code == 302
    return WorkplaceSurveyRecord.objects.get(), response.url, preparation


def test_landing_has_two_help_links_and_keeps_author_credit(client):
    html = client.get("/").content.decode()
    assert html.count(">Recevoir de l’aide</a>") == 2
    assert html.count('href="/aide/"') == 2
    assert "Conçu par un développeur web indépendant" in html
    assert "cdn.tailwindcss.com" not in html
    assert client.get("/surveys/new/").status_code == 404


@pytest.mark.parametrize("page", ["legal", "privacy", "ethics", "contact"])
def test_information_pages(client, page):
    assert client.get(reverse("information-page", args=[page])).status_code == 200
    assert client.get(reverse("information-page", args=["missing"])).status_code == 404


def test_help_form_empty_selection_and_skip_survey(client):
    route = reverse("request-help")
    csrf = Client(enforce_csrf_checks=True)
    data = {"email": EMAIL, "flow": token(csrf, route)}
    assert csrf.post(route, data).status_code == 403
    response = csrf.post(route, {**data, "csrfmiddlewaretoken": csrf.cookies["csrftoken"].value})
    assert response.status_code == 302
    confirmation = csrf.get(response.url)
    assert b"Pas maintenant" in confirmation.content
    assert "no-store" in confirmation["Cache-Control"]
    assert confirmation["Referrer-Policy"] == "same-origin"
    assert EMAIL.encode() not in confirmation.content
    assert HelpRequestRecord.objects.get().situations == []
    assert WorkplaceSurveyRecord.objects.count() == 0
    assert Client().get(response.url).status_code == 404
    assert client.put(route).status_code == 405


def test_help_form_validation_and_replay(client):
    route = reverse("request-help")
    flow = token(client, route)
    invalid = client.post(route, {"flow": flow, "email": "invalid", "situations": ["bad-choice"]})
    assert invalid.status_code == 400
    assert invalid.context["flow"] == flow
    assert set(invalid.context["form"].errors) == {"email", "situations"}
    expired = client.post(route, {"flow": "bad", "email": EMAIL})
    assert expired.status_code == 400
    assert "expiré" in expired.content.decode()
    assert not HelpRequestRecord.objects.exists()
    for email in (EMAIL, "changed@example.com"):
        assert client.post(route, {"flow": flow, "email": email}).status_code == 302
    assert HelpRequestRecord.objects.get().email == EMAIL


@pytest.mark.parametrize("seed", [False, True])
def test_survey_creation_share_and_replay(client, seed):
    poll, ready, preparation = create(client, seed=seed)
    before = client.get(preparation)
    assert b"Ajouter mes situations comme" in before.content
    assert b'checked' not in before.content
    assert client.post(preparation, {"name": "x" * 201}).status_code == 400
    assert client.post(preparation, {"name": "New name"}).url == ready
    assert WorkplaceSurveyRecord.objects.count() == 1
    assert poll.response_count == int(seed)
    assert VoteReceipt.objects.count() == int(seed)
    assert poll.name == "Dépôt Sud"
    assert Client().get(ready).status_code == 404
    response = client.get(ready)
    assert response.status_code == 200
    assert EMAIL.encode() not in response.content
    assert response.context["deletion_key"] not in poll.deletion_key_hash
    share = parse_qs(urlparse(response.context["whatsapp_url"]).query)["text"][0]
    assert share == f"Salut ! Voici un petit sondage sur nos conditions de travail. Si tu veux y répondre : http://testserver/s/{poll.public_id}/"
    route = reverse("take-survey", args=[poll.public_id])
    assert client.post(route, {"none_applies": "on"}).status_code == 302
    poll.refresh_from_db()
    assert poll.response_count == 1


def test_no_seed_choice_for_empty_help_request_and_confirmation_expires(client):
    preparation = prepare(client)
    assert b"Ajouter mes situations" not in client.get(preparation).content
    assert client.post(preparation, {"include_situations": "on"}).status_code == 302
    poll = WorkplaceSurveyRecord.objects.get()
    assert poll.name == "Votre équipe"
    assert poll.response_count == 0
    HelpRequestRecord.objects.update(created_at=timezone.now() - timedelta(hours=1, seconds=1))
    assert client.get(preparation).status_code == 404


def test_protected_survey_gate_applies_to_every_public_entrypoint(client):
    poll, _, _ = create(client, password="open sesame")
    for name in ("take-survey", "results", "survey-help"):
        guest = Client()
        path = reverse(name, args=[poll.public_id])
        assert guest.get(path).status_code == 403
        assert guest.post(path, {}).status_code == 403
        assert guest.post(path, {"survey_password": "wrong"}).status_code == 403
        assert guest.post(path, {"survey_password": "open sesame"}).url == path
        assert guest.get(path).status_code == 200
        assert client.get(path).status_code == 200
    assert poll.password_hash != "open sesame"
    assert not VoteReceipt.objects.exists()


def test_threshold_and_contextual_help_are_independent(client):
    poll, _, _ = create(client)
    vote_url = reverse("take-survey", args=[poll.public_id])
    result_url = reverse("results", args=[poll.public_id])
    help_url = reverse("survey-help", args=[poll.public_id])
    expected = (
        "à partir de 3 réponses", "Encore 2 réponses", "Plus qu’une réponse",
        "3 réponses enregistrées", "4 réponses enregistrées",
    )
    for count in range(5):
        visitor = Client()
        result = visitor.get(result_url)
        assert expected[count] in result.content.decode()
        assert (b"<meter" in result.content) is (count >= 3)
        assert f'href="{help_url}"'.encode() in result.content
        if count in (0, 4):
            response = ask(visitor, help_url, email=f"colleague{count}@example.com", situations=[Situation.HEALTH])
            assert response.status_code == 302
            confirmation = visitor.get(response.url)
            assert b"Retourner aux" in confirmation.content
            assert visitor.get(response.url.replace("/confirmation/", "/partage/")).status_code == 404
            assert visitor.get(response.url.replace("/confirmation/", "/lien/")).status_code == 404
        if count < 4:
            assert visitor.get(vote_url).status_code == 200
            data = {"situations": [Situation.PAY]} if count % 2 else {"none_applies": "on"}
            assert visitor.post(vote_url, data).url == result_url
            assert "Ta réponse a été enregistrée." in visitor.get(result_url).content.decode()
            assert visitor.post(vote_url, data).url == result_url
            assert "déjà été enregistrée" in visitor.get(result_url).content.decode()
    requests = HelpRequestRecord.objects.filter(from_survey=True, survey_id=poll.public_id)
    assert [request.situations for request in requests] == [[Situation.HEALTH], [Situation.HEALTH]]
    poll.refresh_from_db()
    assert poll.response_count == 4
    assert poll.counts == [0, 0, 0, 0, 2]
    assert "2 réponses sur 4" in client.get(result_url).content.decode()
    assert "0 réponse sur 4" in client.get(result_url).content.decode()


@pytest.mark.parametrize("payload", [{}, {"none_applies": "on", "situations": ["pay"]}, {"situations": ["invalid"]}])
def test_ballot_validation_keeps_results_unchanged(client, payload):
    poll, _, _ = create(client)
    route = reverse("take-survey", args=[poll.public_id])
    assert client.post(route, payload).status_code == 400
    assert not VoteReceipt.objects.exists()


def test_contextual_form_rejects_a_token_from_another_context(client):
    poll, _, _ = create(client)
    help_url = reverse("survey-help", args=[poll.public_id])
    assert client.post(help_url, {"flow": token(client, "/aide/"), "email": EMAIL}).status_code == 400
    assert HelpRequestRecord.objects.count() == 1


def test_delete_does_not_affect_help_or_allow_recreation(client):
    poll, ready, preparation = create(client, seed=True)
    url = reverse("delete-survey", args=[poll.public_id])
    assert client.get(url).status_code == 200
    assert client.post(url, {"deletion_key": "wrong"}).status_code == 400
    key = client.get(ready).context["deletion_key"]
    assert client.post(url, {"deletion_key": key}).url == "/"
    assert not VoteReceipt.objects.exists()
    assert HelpRequestRecord.objects.exists()
    assert client.get(ready).status_code == 404
    assert client.post(preparation, {}).status_code == 404
    assert client.get(reverse("take-survey", args=[poll.public_id])).status_code == 404


def test_vote_deleted_between_read_and_write_returns_404(client, monkeypatch):
    poll, _, _ = create(client)
    url = reverse("take-survey", args=[poll.public_id])
    original = DjangoSurveyRepository.add_ballot

    def delete_before_ballot(repo, public_id, receipt, ballot):
        repo.delete(public_id)
        return original(repo, public_id, receipt, ballot)

    monkeypatch.setattr(DjangoSurveyRepository, "add_ballot", delete_before_ballot)
    assert client.post(url, {"none_applies": "on"}).status_code == 404
