from unittest.mock import patch

import pytest
from django.test import override_settings

from contacts.models import ContactRequestRecord
from contacts.repositories import DjangoContactRepository
from domain.entities import ContactRequest


@override_settings(
    CONTACT_NOTIFICATION_RECIPIENTS=["operator@example.com"],
    DEFAULT_FROM_EMAIL="notifications@example.com",
)
@pytest.mark.django_db(databases=["default", "contacts"])
def test_contact_notification_contains_no_submitter_data():
    request = ContactRequest("private@example.com", True, False, "Private team")

    with (
        patch("contacts.repositories.transaction.on_commit", side_effect=lambda callback, using, robust: callback()),
        patch("contacts.repositories.send_mail") as send_mail,
    ):
        DjangoContactRepository().add(request)

    subject, body, sender, recipients = send_mail.call_args.args[:4]
    assert subject == "Nouvelle demande de mise en relation Bokebi"
    assert "private@example.com" not in body
    assert "Private team" not in body
    assert sender == "notifications@example.com"
    assert recipients == ["operator@example.com"]
    assert send_mail.call_args.kwargs["fail_silently"] is False


@override_settings(
    CONTACT_NOTIFICATION_RECIPIENTS=["operator@example.com"],
    DEFAULT_FROM_EMAIL="notifications@example.com",
)
@pytest.mark.django_db(transaction=True, databases=["default", "contacts"])
def test_contact_request_is_saved_when_notification_times_out():
    request = ContactRequest("private@example.com", True, False, "Private team")

    with patch("contacts.repositories.send_mail", side_effect=TimeoutError("timed out")):
        DjangoContactRepository().add(request)

    assert ContactRequestRecord.objects.using("contacts").filter(
        email="private@example.com"
    ).exists()
