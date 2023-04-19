from django.db import models
from django.template.defaultfilters import slugify


CATEGORY_CHOICES = [
    ('Hybrid', 'Hybrid'),
    ('Sativa', 'Sativa'),
    ('Indica', 'Indica'),
]

FEELING_CHOICES = [
    ('Uplifted', 'Uplifted'),
    ('Euphoric', 'Euphoric'),
    ('Energetic', 'Energetic'),
]

NEGATIVE_CHOICES = [
    ('Dizzy', 'Dizzy'),
    ('Anxious', 'Anxious'),
    ('Paranoid', 'Paranoid'),
]

HELPS_WITH_CHOICES = [
    ('Anxiety', 'Anxiety'),
    ('Depression', 'Depression'),
    ('Stress', 'Stress'),
]

FLAVOR_CHOICES = [
    ('Butter', 'Butter'),
    ('Vanilla', 'Vanilla'),
    ('Citrus', 'Citrus'),
]


class Strain(models.Model):
    name = models.CharField(max_length=255)
    cbd = models.DecimalField(max_digits=5, decimal_places=2, null=True)
    thc = models.DecimalField(max_digits=5, decimal_places=2)
    cbg = models.DecimalField(max_digits=5, decimal_places=2, null=True)
    rating = models.DecimalField(max_digits=3, decimal_places=1)
    img = models.ImageField(upload_to='strains/', blank=True, null=True)
    category = models.CharField(max_length=10, choices=CATEGORY_CHOICES)
    feelings = models.ManyToManyField('Feeling')
    negatives = models.ManyToManyField('Negative')
    helps_with = models.ManyToManyField('HelpsWith')
    flavors = models.ManyToManyField('Flavor')
    text_content = models.TextField()
    description = models.CharField(max_length=255)
    keywords = models.CharField(max_length=255)
    slug = models.SlugField(unique=True, default='')

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Feeling(models.Model):
    name = models.CharField(max_length=50, unique=True, choices=FEELING_CHOICES)

    def __str__(self):
        return self.name


class Negative(models.Model):
    name = models.CharField(max_length=50, unique=True, choices=NEGATIVE_CHOICES)

    def __str__(self):
        return self.name


class HelpsWith(models.Model):
    name = models.CharField(max_length=50, unique=True, choices=HELPS_WITH_CHOICES)

    def __str__(self):
        return self.name


class Flavor(models.Model):
    name = models.CharField(max_length=50, unique=True, choices=FLAVOR_CHOICES)

    def __str__(self):
        return self.name
