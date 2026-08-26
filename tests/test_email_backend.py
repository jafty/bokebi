import json
from unittest.mock import MagicMock, patch

from django.core.mail import EmailMessage

from contacts.email_backend import BrevoEmailBackend


def test_brevo_backend_sends_email_through_transactional_api(settings):
    settings.BREVO_API_KEY = "secret-api-key"
    settings.BREVO_SENDER_EMAIL = "verified@example.com"
    settings.EMAIL_TIMEOUT = 7
    response = MagicMock()
    response.__enter__.return_value = response

    with patch("contacts.email_backend.urlopen", return_value=response) as urlopen:
        sent = BrevoEmailBackend().send_messages([
            EmailMessage("New request", "Open the admin.", None, ["staff@example.com"])
        ])

    assert sent == 1
    request = urlopen.call_args.args[0]
    assert request.full_url == "https://api.brevo.com/v3/smtp/email"
    assert request.headers["Api-key"] == "secret-api-key"
    assert json.loads(request.data) == {
        "sender": {"email": "verified@example.com"},
        "to": [{"email": "staff@example.com"}],
        "subject": "New request",
        "textContent": "Open the admin.",
    }
    assert urlopen.call_args.kwargs == {"timeout": 7}


def test_brevo_backend_honors_fail_silently(settings):
    settings.BREVO_API_KEY = "secret-api-key"
    settings.BREVO_SENDER_EMAIL = "verified@example.com"

    with patch("contacts.email_backend.urlopen", side_effect=TimeoutError):
        sent = BrevoEmailBackend(fail_silently=True).send_messages([
            EmailMessage("Subject", "Body", None, ["staff@example.com"])
        ])

    assert sent == 0
