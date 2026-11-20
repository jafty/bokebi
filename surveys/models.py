from django.db import models

from domain.entities import Situation


def empty_counts():
    return [0] * len(Situation)


class WorkplaceSurveyRecord(models.Model):
    public_id = models.CharField(max_length=32, unique=True)
    name = models.CharField(max_length=200)
    deletion_key_hash = models.CharField(max_length=256)
    password_hash = models.CharField(max_length=256, null=True)
    created_at = models.DateTimeField()
    response_count = models.PositiveIntegerField(default=0)
    counts = models.JSONField(default=empty_counts)

    def __str__(self):
        return self.name


class VoteReceipt(models.Model):
    survey = models.ForeignKey(WorkplaceSurveyRecord, on_delete=models.CASCADE)
    digest = models.CharField(max_length=64)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["survey", "digest"], name="unique_survey_vote_receipt"),
        ]


class SurveyCreationReceipt(models.Model):
    public_id = models.CharField(max_length=32, primary_key=True)
    created_at = models.DateTimeField(db_index=True)
