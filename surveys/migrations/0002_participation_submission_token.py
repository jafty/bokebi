import secrets

from django.db import migrations, models


def populate_submission_tokens(apps, schema_editor):
    participation = apps.get_model("surveys", "ParticipationRecord")
    for row in participation.objects.filter(submission_token="").iterator():
        row.submission_token = secrets.token_urlsafe(32)
        row.save(update_fields=("submission_token",))


class Migration(migrations.Migration):
    dependencies = [("surveys", "0001_initial")]
    operations = [
        migrations.AddField(
            model_name="participationrecord",
            name="submission_token",
            field=models.CharField(default="", max_length=64),
            preserve_default=False,
        ),
        migrations.RunPython(populate_submission_tokens, migrations.RunPython.noop),
        migrations.AddConstraint(
            model_name="participationrecord",
            constraint=models.UniqueConstraint(fields=("survey", "submission_token"), name="unique_survey_submission"),
        ),
    ]
