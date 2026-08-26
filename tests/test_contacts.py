from unittest.mock import patch

import pytest
from django.test import override_settings

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
        patch("contacts.repositories.transaction.on_commit", side_effect=lambda callback, using: callback()),
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
