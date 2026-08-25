from django.db import models

class ContactRequestRecord(models.Model):
    email = models.EmailField()
    wants_colleagues = models.BooleanField(default=False)
    wants_organization = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = "contacts"
