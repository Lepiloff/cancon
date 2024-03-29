# Generated by Django 4.2 on 2024-02-15 08:46

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('strains', '0012_alter_article_slug'),
    ]

    operations = [
        migrations.CreateModel(
            name='AlternativeStrainName',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=255)),
                ('strain', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='alternative_names', to='strains.strain')),
            ],
        ),
    ]
