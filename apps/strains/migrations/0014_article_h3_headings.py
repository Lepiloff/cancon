# Generated by Django 4.2.16 on 2024-09-23 10:26

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('strains', '0013_alternativestrainname'),
    ]

    operations = [
        migrations.AddField(
            model_name='article',
            name='h3_headings',
            field=models.JSONField(blank=True, default=list, null=True),
        ),
    ]
