import logging
from datetime import timedelta
from urllib.error import HTTPError

from django.conf import settings
from django.core.mail import send_mail
from django.db import transaction
from django.urls import reverse
from django.utils import timezone

from .models import HelpRequestRecord

logger = logging.getLogger(__name__)
RETRY_DELAY = timedelta(minutes=5)


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
