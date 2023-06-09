# Generated by Django 4.2 on 2023-04-30 09:26

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Article',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=255)),
                ('text_content', models.TextField()),
                ('description', models.CharField(max_length=255)),
                ('keywords', models.CharField(max_length=255)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('canonical_url', models.URLField(blank=True, null=True)),
                ('slug', models.SlugField(default='', unique=True)),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='ArticleCategory',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=50, unique=True)),
            ],
        ),
        migrations.CreateModel(
            name='Feeling',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=50, unique=True)),
            ],
        ),
        migrations.CreateModel(
            name='Flavor',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=50, unique=True)),
            ],
        ),
        migrations.CreateModel(
            name='HelpsWith',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=50, unique=True)),
            ],
        ),
        migrations.CreateModel(
            name='Negative',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=50, unique=True)),
            ],
        ),
        migrations.CreateModel(
            name='Terpene',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=50, unique=True)),
            ],
        ),
        migrations.CreateModel(
            name='Strain',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=255)),
                ('text_content', models.TextField()),
                ('description', models.CharField(max_length=255)),
                ('keywords', models.CharField(max_length=255)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('canonical_url', models.URLField(blank=True, null=True)),
                ('name', models.CharField(max_length=255)),
                ('cbd', models.DecimalField(decimal_places=2, max_digits=5, null=True)),
                ('thc', models.DecimalField(decimal_places=2, max_digits=5)),
                ('cbg', models.DecimalField(decimal_places=2, max_digits=5, null=True)),
                ('rating', models.DecimalField(decimal_places=1, max_digits=3)),
                ('img', models.ImageField(blank=True, null=True, upload_to='strains/images')),
                ('img_alt_text', models.CharField(blank=True, max_length=255, null=True)),
                ('category', models.CharField(choices=[('Hybrid', 'Hybrid'), ('Sativa', 'Sativa'), ('Indica', 'Indica')], max_length=10)),
                ('slug', models.SlugField(default='', unique=True)),
                ('active', models.BooleanField(default=False)),
                ('feelings', models.ManyToManyField(to='strains.feeling')),
                ('flavors', models.ManyToManyField(to='strains.flavor')),
                ('helps_with', models.ManyToManyField(to='strains.helpswith')),
                ('negatives', models.ManyToManyField(to='strains.negative')),
                ('terpenes', models.ManyToManyField(blank=True, to='strains.terpene')),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='ArticleImage',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('img', models.ImageField(upload_to='articles/images/')),
                ('img_alt_text', models.CharField(blank=True, max_length=255, null=True)),
                ('is_preview', models.BooleanField(default=False)),
                ('article', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='images', to='strains.article')),
            ],
        ),
        migrations.AddField(
            model_name='article',
            name='category',
            field=models.ManyToManyField(to='strains.articlecategory'),
        ),
    ]
