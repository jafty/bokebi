from domain.ports import ContactRepository
from .models import ContactRequestRecord

class DjangoContactRepository(ContactRepository):
    def add(self, request):
        ContactRequestRecord.objects.using("contacts").create(email=request.email, wants_colleagues=request.wants_colleagues, wants_organization=request.wants_organization)
