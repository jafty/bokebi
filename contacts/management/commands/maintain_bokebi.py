from datetime import timedelta

from django.core.management.base import BaseCommand

from contacts.models import HelpRequestRecord
from contacts.notifications import send_help_notification
from contacts.repositories import DjangoHelpRepository
from domain.use_cases import MaintainHelpRequests
from surveys.gateways import SystemClock
from surveys.models import SurveyCreationReceipt


class Command(BaseCommand):
    help = "Réessaie les alertes Bokebi et purge les demandes closes depuis 30 jours."

    def handle(self, *args, **options):
        clock = SystemClock()
        now = clock.now()
        purged = MaintainHelpRequests(DjangoHelpRepository(), clock).purge()
        SurveyCreationReceipt.objects.filter(created_at__lt=now - timedelta(days=1)).delete()
        requests = HelpRequestRecord.objects.filter(notification_due_at__lte=now)
        for request_id in requests.values_list("pk", flat=True).iterator():
            send_help_notification(request_id, clock.now())
        self.stdout.write(f"Demandes closes purgées : {purged}")
