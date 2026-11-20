from datetime import timedelta
from uuid import uuid4

import pytest
from django.core import mail
from django.core.management import call_command
from django.urls import reverse
from django.utils import timezone

from contacts.models import HelpRequestRecord
from contacts.notifications import send_help_notification
from domain.entities import HelpStatus, Situation
from surveys.models import SurveyCreationReceipt, WorkplaceSurveyRecord
from test_views import ask, create, token

pytestmark = pytest.mark.django_db(databases=["default", "contacts"])
QUEUE = "admin:contacts_helprequestrecord_changelist"


def test_alert_after_commit_is_generic_and_sent_once(client, settings, django_capture_on_commit_callbacks):
    settings.CONTACT_NOTIFICATION_RECIPIENTS = ["operator@example.com"]
    settings.BOKEBI_PUBLIC_URL = "https://bokebi.example"
    form_token = token(client, "/aide/")
    data = {"email": "submitter@example.com", "flow": form_token, "situations": [Situation.HEALTH]}
    with django_capture_on_commit_callbacks(using="contacts", execute=True):
        assert client.post("/aide/", data).status_code == 302
        assert client.post("/aide/", data).status_code == 302
    assert len(mail.outbox) == 1
    [alert] = mail.outbox
    assert alert.to == ["operator@example.com"]
    assert f"https://bokebi.example{reverse(QUEUE)}" in alert.body
    record = HelpRequestRecord.objects.get()
    assert all(value not in alert.body for value in (record.email, str(record.id), record.survey_id, str(Situation.HEALTH)))
    assert record.notification_due_at is None


def test_timeout_keeps_request_and_retries_only_when_due(
    client, settings, monkeypatch, django_capture_on_commit_callbacks, caplog,
):
    settings.CONTACT_NOTIFICATION_RECIPIENTS = ["operator@example.com"]

    def timeout(*args, **kwargs):
        raise TimeoutError("private diagnostic text")

    with monkeypatch.context() as patch:
        patch.setattr("contacts.notifications.send_mail", timeout)
        with django_capture_on_commit_callbacks(using="contacts", execute=True):
            assert ask(client).status_code == 302
    row = HelpRequestRecord.objects.get()
    assert row.notification_due_at > row.created_at
    assert "TimeoutError" in caplog.text
    assert "private diagnostic text" not in caplog.text
    send_help_notification(row.pk, row.created_at)
    assert not mail.outbox
    HelpRequestRecord.objects.update(notification_due_at=timezone.now())
    call_command("maintain_bokebi")
    assert len(mail.outbox) == 1
    row.refresh_from_db()
    assert row.notification_due_at is None


@pytest.mark.parametrize("recipients", [[], ["operator@example.com"]])
def test_unconfigured_or_unsent_alert_remains_due(client, settings, monkeypatch, recipients):
    settings.CONTACT_NOTIFICATION_RECIPIENTS = recipients
    monkeypatch.setattr("contacts.notifications.send_mail", lambda *args: 0)
    ask(client)
    row = HelpRequestRecord.objects.get()
    send_help_notification(row.pk, timezone.now())
    row.refresh_from_db()
    assert row.notification_due_at > timezone.now()


def test_maintenance_purges_only_closed_dossiers_and_stale_creation_receipts(client):
    poll, _, _ = create(client, seed=True)
    now = timezone.now()
    cutoff = now - timedelta(days=30)
    initial = HelpRequestRecord.objects.get()
    initial.status = HelpStatus.CLOSED
    initial.closed_at = cutoff
    initial.save(update_fields=["status", "closed_at"])
    recently_closed = HelpRequestRecord.objects.create(
        id=uuid4(), email="closed@example.com", from_survey=True, survey_id=poll.public_id,
        created_at=cutoff, status=HelpStatus.CLOSED, closed_at=cutoff + timedelta(minutes=5),
    )
    pending = HelpRequestRecord.objects.create(
        id=uuid4(), email="pending@example.com", from_survey=True, survey_id=poll.public_id,
        created_at=cutoff,
    )
    SurveyCreationReceipt.objects.create(public_id="expired", created_at=now - timedelta(days=2))
    call_command("maintain_bokebi")
    assert set(HelpRequestRecord.objects.values_list("pk", flat=True)) == {recently_closed.pk, pending.pk}
    assert list(SurveyCreationReceipt.objects.values_list("public_id", flat=True)) == [poll.public_id]
    assert WorkplaceSurveyRecord.objects.get().response_count == 1


def test_admin_is_private_and_groups_requests(client, admin_client, django_user_model):
    poll, _, _ = create(client)
    ask(client, f"/s/{poll.public_id}/aide/", email="colleague@example.com", situations=[Situation.OVERTIME])
    HelpRequestRecord.objects.update(created_at=timezone.now() - timedelta(hours=25))
    queue = reverse(QUEUE)
    assert client.get(queue).status_code == 302
    client.force_login(django_user_model.objects.create_user(username="staff", is_staff=True))
    assert client.get(queue).status_code == 403
    listing = admin_client.get(queue)
    assert b"colleague@example.com" in listing.content
    assert b"en retard" in listing.content
    assert b"Demande initiale" in listing.content
    narrowed = admin_client.get(queue, {"survey_id__exact": poll.public_id})
    assert narrowed.status_code == 200
    assert len(narrowed.context["cl"].result_list) == 2
    record = HelpRequestRecord.objects.get(from_survey=True)
    detail = reverse("admin:contacts_helprequestrecord_change", args=[record.pk])
    assert "ni payées ni récupérées" in admin_client.get(detail).content.decode()
    assert admin_client.get(reverse("admin:contacts_helprequestrecord_add")).status_code == 403
    assert admin_client.get(reverse("admin:contacts_helprequestrecord_delete", args=[record.pk])).status_code == 403
    poll.delete()
    listing = admin_client.get(queue)
    assert b"Aucun sondage actif" in listing.content
    assert "Sondage supprimé" in listing.content.decode()


def test_admin_status_actions_enforce_domain_rules_and_stop_notifications(client, admin_client):
    ask(client)
    queue = reverse(QUEUE)
    record = HelpRequestRecord.objects.get()
    selection = {"_selected_action": [str(record.pk)]}
    invalid = admin_client.post(queue, {"action": "mark_in_progress", **selection}, follow=True)
    assert b"sans changement de statut" in invalid.content
    for action, status in (
        ("mark_contacted", HelpStatus.CONTACTED),
        ("mark_in_progress", HelpStatus.IN_PROGRESS),
        ("mark_closed", HelpStatus.CLOSED),
    ):
        assert admin_client.post(queue, {"action": action, **selection}).status_code == 302
        record.refresh_from_db()
        assert record.status == status
    assert record.notification_due_at is None
    assert record.created_at <= record.contacted_at <= record.closed_at


def test_survey_admin_only_shows_aggregate_after_threshold(client, admin_client):
    poll, _, _ = create(client, seed=True)
    detail = reverse("admin:surveys_workplacesurveyrecord_change", args=[poll.pk])
    assert b"Disponibles" in admin_client.get(detail).content
    poll.response_count = 3
    poll.save(update_fields=["response_count"])
    assert b"1 sur 3" in admin_client.get(detail).content
    assert admin_client.get(reverse("admin:surveys_workplacesurveyrecord_add")).status_code == 403
    assert admin_client.get(reverse("admin:surveys_workplacesurveyrecord_delete", args=[poll.pk])).status_code == 403
    assert admin_client.post(detail, {"name": "Tampered"}).status_code == 403


def test_idempotent_new_status_keeps_pending_notification(client):
    from contacts.repositories import DjangoHelpRepository

    ask(client)
    row = HelpRequestRecord.objects.get()
    due = row.notification_due_at
    DjangoHelpRepository().transition(row.pk, HelpStatus.NEW, timezone.now())
    row.refresh_from_db()
    assert row.notification_due_at == due


def test_brevo_http_failure_logs_status_without_response_body(client, settings, monkeypatch, caplog):
    from io import BytesIO
    from urllib.error import HTTPError

    settings.CONTACT_NOTIFICATION_RECIPIENTS = ["operator@example.com"]

    def fail(*args):
        raise HTTPError("https://api.brevo.com", 401, "unauthorized", {}, BytesIO(b"private data"))

    monkeypatch.setattr("contacts.notifications.send_mail", fail)
    ask(client)
    row = HelpRequestRecord.objects.get()
    send_help_notification(row.pk, timezone.now())
    row.refresh_from_db()
    assert "Brevo HTTP 401" in caplog.text
    assert "private data" not in caplog.text
    assert row.notification_due_at is not None
