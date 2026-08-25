from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("contacts", "0001_initial")]
    operations = [
        migrations.AddField(
            model_name="contactrequestrecord",
            name="contacted_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AlterModelOptions(
            name="contactrequestrecord",
            options={"ordering": ("-created_at",)},
        ),
    ]
