from django.db import models

from domain.entities import HelpStatus


STATUS_CHOICES = (
    (HelpStatus.NEW, "Nouveau"),
    (HelpStatus.CONTACTED, "Contacté"),
    (HelpStatus.IN_PROGRESS, "En cours"),
    (HelpStatus.CLOSED, "Clos"),
)


class HelpRequestRecord(models.Model):
    id = models.UUIDField(primary_key=True, editable=False)
    email = models.EmailField()
    situations = models.JSONField(default=list)
    survey_id = models.CharField(max_length=32, db_index=True)
    from_survey = models.BooleanField()
    created_at = models.DateTimeField()
    status = models.CharField(max_length=16, default=HelpStatus.NEW, choices=STATUS_CHOICES)
    contacted_at = models.DateTimeField(null=True)
    closed_at = models.DateTimeField(null=True, db_index=True)
    notification_due_at = models.DateTimeField(null=True, db_index=True)

    class Meta:
        ordering = ("created_at",)

    def __str__(self):
        return f"Demande {self.pk}"
