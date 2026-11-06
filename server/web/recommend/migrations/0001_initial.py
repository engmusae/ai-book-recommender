from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True
    dependencies = []
    operations = [
        migrations.CreateModel(
            name="Recommendation",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("request_text", models.TextField(max_length=300)),
                ("score", models.PositiveSmallIntegerField(blank=True, null=True)),
                ("reason", models.TextField(blank=True)),
                ("image", models.ImageField(blank=True, upload_to="images/")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
        ),
    ]
