import json
from urllib.request import Request, urlopen

from django.conf import settings
from django.core.mail.backends.base import BaseEmailBackend


class BrevoEmailBackend(BaseEmailBackend):
    """Send Django email messages through Brevo's transactional HTTP API."""

    endpoint = "https://api.brevo.com/v3/smtp/email"

    def send_messages(self, email_messages):
        if not email_messages:
            return 0

        sent = 0
        for message in email_messages:
            payload = {
                "sender": {"email": settings.BREVO_SENDER_EMAIL},
                "to": [{"email": address} for address in message.to],
                "subject": message.subject,
                "textContent": message.body,
            }
            request = Request(
                self.endpoint,
                data=json.dumps(payload).encode(),
                headers={
                    "accept": "application/json",
                    "api-key": settings.BREVO_API_KEY,
                    "content-type": "application/json",
                },
                method="POST",
            )
            try:
                with urlopen(request, timeout=settings.EMAIL_TIMEOUT):
                    sent += 1
            except Exception:
                if not self.fail_silently:
                    raise
        return sent
