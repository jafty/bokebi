import json
import logging
import re
from datetime import timedelta
from http.client import HTTPException
from ipaddress import ip_address
from urllib.error import HTTPError

from django.conf import settings
from django.core.mail import send_mail
from django.db import transaction
from django.urls import reverse
from django.utils import timezone

from .models import HelpRequestRecord

logger = logging.getLogger(__name__)
RETRY_DELAY = timedelta(minutes=5)


def _brevo_auth_failure(error):
    unknown_reason = "authentification refusée sans motif reconnu"
    try:
        with error:
            response = json.loads(error.read(4096))
    except (HTTPException, OSError, RecursionError, ValueError):
        return unknown_reason

    message = response.get("message") if isinstance(response, dict) else None
    if not isinstance(message, str):
        return unknown_reason

    message = message.casefold()
    unrecognized_ip = re.search(
        r"\bunrecogni[sz]ed ip address\b(?:\s+([0-9a-f:.]+)(?!\S))?", message,
    )
    if unrecognized_ip:
        address = unrecognized_ip.group(1) or ""
        try:
            return f"adresse IP non autorisée ({ip_address(address.rstrip('.'))})"
        except ValueError:
            return "adresse IP non autorisée"
    if any(phrase in message for phrase in ("key not found", "invalid api key", "missing api key")):
        return "clé API absente ou invalide"
    return unknown_reason


@transaction.atomic(using="contacts")
def send_help_notification(request_id, now):
    row = HelpRequestRecord.objects.select_for_update().filter(
        pk=request_id, notification_due_at__lte=now,
    ).first()
    if row is None:
        return
    delivered = False
    recipients = settings.CONTACT_NOTIFICATION_RECIPIENTS
    if recipients:
        queue_path = reverse("admin:contacts_helprequestrecord_changelist")
        try:
            delivered = send_mail(
                "Nouvelle demande d’aide Bokebi",
                f"Une demande est disponible dans l’espace Bokebi.\n{settings.BOKEBI_PUBLIC_URL}{queue_path}",
                settings.DEFAULT_FROM_EMAIL,
                recipients,
            ) == 1
        except HTTPError as error:
            if error.code == 401:
                logger.error("Échec de notification Bokebi (Brevo HTTP 401 : %s).", _brevo_auth_failure(error))
            else:
                logger.error("Échec de notification Bokebi (Brevo HTTP %s).", error.code)
        except Exception as error:
            logger.error("Échec de notification Bokebi (%s).", type(error).__name__)
    row.notification_due_at = None if delivered else now + RETRY_DELAY
    row.save(update_fields=["notification_due_at"])



class DjangoHelpNotifications:
    def request_received(self, request_id):
        transaction.on_commit(
            lambda: send_help_notification(request_id, timezone.now()),
            using="contacts", robust=True,
        )
