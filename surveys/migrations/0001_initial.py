from django.db import migrations, models
import django.db.models.deletion

class Migration(migrations.Migration):
    initial = True
    dependencies = []
    operations = [
        migrations.CreateModel(name="SurveyRecord", fields=[("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")), ("public_id", models.CharField(db_index=True, max_length=32, unique=True)), ("team_name", models.CharField(max_length=200)), ("deletion_key_hash", models.CharField(max_length=256)), ("password_hash", models.CharField(blank=True, max_length=256, null=True)), ("created_at", models.DateTimeField())]),
        migrations.CreateModel(name="ParticipationRecord", fields=[("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")), ("answers", models.JSONField()), ("created_at", models.DateTimeField(auto_now_add=True)), ("survey", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="participations", to="surveys.surveyrecord"))]),
    ]
