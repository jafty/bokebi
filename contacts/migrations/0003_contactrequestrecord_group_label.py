from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("contacts", "0002_contactrequestrecord_contacted_at")]
    operations = [
        migrations.AddField(
            model_name="contactrequestrecord",
            name="group_label",
            field=models.CharField(default="Groupe non renseigné", max_length=200),
            preserve_default=False,
        ),
    ]
