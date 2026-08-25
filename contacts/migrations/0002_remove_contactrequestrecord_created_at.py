from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [("contacts", "0001_initial")]

    operations = [
        migrations.RemoveField(
            model_name="contactrequestrecord",
            name="created_at",
        ),
    ]
