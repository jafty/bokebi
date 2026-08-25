from django.db import models

class SurveyRecord(models.Model):
    public_id = models.CharField(max_length=32, unique=True, db_index=True)
    team_name = models.CharField(max_length=200)
    deletion_key_hash = models.CharField(max_length=256)
    password_hash = models.CharField(max_length=256, null=True, blank=True)
    created_at = models.DateTimeField()

class ParticipationRecord(models.Model):
    survey = models.ForeignKey(SurveyRecord, on_delete=models.CASCADE, related_name="participations")
    answers = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)
