# Generated by Django 4.2 on 2023-05-01 13:41

from django.db import migrations
import tinymce.models


class Migration(migrations.Migration):

    dependencies = [
        ('strains', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='article',
            name='text_content',
            field=tinymce.models.HTMLField(),
        ),
        migrations.AlterField(
            model_name='strain',
            name='text_content',
            field=tinymce.models.HTMLField(),
        ),
    ]
