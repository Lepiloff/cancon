from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('strains', '0016_migrate_spanish_content'),
    ]

    operations = [
        migrations.AlterField(
            model_name='strain',
            name='rating',
            field=models.DecimalField(blank=True, decimal_places=1, max_digits=3, null=True),
        ),
    ]
