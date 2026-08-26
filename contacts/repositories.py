from django.conf import settings
from django.core.mail import send_mail
from django.db import transaction

from domain.ports import ContactRepository
from .models import ContactRequestRecord

class DjangoContactRepository(ContactRepository):
    def add(self, request):
        ContactRequestRecord.objects.using("contacts").create(email=request.email, wants_colleagues=request.wants_colleagues, wants_organization=request.wants_organization, group_label=request.group_label)
        if settings.CONTACT_NOTIFICATION_RECIPIENTS:
            transaction.on_commit(
                lambda: send_mail(
                    "Nouvelle demande de mise en relation Bokebi",
                    "Une nouvelle demande est disponible dans l’espace opérateur. "
                    "Connectez-vous à /admin/contacts/contactrequestrecord/. "
                    "Aucune coordonnée n’est incluse dans cet e-mail afin de préserver sa confidentialité.",
                    settings.DEFAULT_FROM_EMAIL,
                    settings.CONTACT_NOTIFICATION_RECIPIENTS,
                    fail_silently=False,
                ),
                using="contacts",
                # A notification is best-effort: the contact request has already
                # been saved and an unavailable SMTP server must not turn the
                # submitter's successful opt-in into an HTTP 500 response.
                robust=True,
            )
