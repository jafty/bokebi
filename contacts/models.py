from django.db import models

class ContactRequestRecord(models.Model):
    email = models.EmailField()
    wants_colleagues = models.BooleanField(default=False)
    wants_organization = models.BooleanField(default=False)

    class Meta:
        app_label = "contacts"
