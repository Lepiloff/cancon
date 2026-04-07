from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0003_consumptionnote"),
    ]

    operations = [
        migrations.AddField(
            model_name="customuser",
            name="display_name",
            field=models.CharField(blank=True, max_length=50, verbose_name="display name"),
        ),
    ]
