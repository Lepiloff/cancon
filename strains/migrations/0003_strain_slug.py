# Generated by Django 4.2 on 2023-04-16 13:21

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('strains', '0002_alter_strain_cbd_alter_strain_cbg'),
    ]

    operations = [
        migrations.AddField(
            model_name='strain',
            name='slug',
            field=models.SlugField(default='', unique=True),
        ),
    ]