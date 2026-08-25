from django.db import migrations, models
class Migration(migrations.Migration):
    initial = True
    dependencies = []
    operations = [migrations.CreateModel(name="ContactRequestRecord", fields=[("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")), ("email", models.EmailField(max_length=254)), ("wants_colleagues", models.BooleanField(default=False)), ("wants_organization", models.BooleanField(default=False)), ("created_at", models.DateTimeField(auto_now_add=True))])]
