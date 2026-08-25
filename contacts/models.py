from django.db import models

class ContactRequestRecord(models.Model):
    email = models.EmailField()
    wants_colleagues = models.BooleanField(default=False)
    wants_organization = models.BooleanField(default=False)
    group_label = models.CharField(max_length=200)
    created_at = models.DateTimeField(auto_now_add=True)
    contacted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        app_label = "contacts"
        ordering = ("-created_at",)

    def __str__(self):
        return self.email
