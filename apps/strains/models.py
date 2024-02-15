from django.db import models
from django.db.models.signals import post_delete
from django.dispatch import receiver
from django.template.defaultfilters import slugify
from tinymce.models import HTMLField


CATEGORY_CHOICES = [
    ('Hybrid', 'Hybrid'),
    ('Sativa', 'Sativa'),
    ('Indica', 'Indica'),
]


class BaseText(models.Model):
    title = models.CharField(max_length=255)
    text_content = HTMLField()
    description = models.CharField(max_length=255)
    keywords = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    canonical_url = models.URLField(blank=True, null=True)

    class Meta:
        abstract = True


class Strain(BaseText):
    name = models.CharField(max_length=255)
    cbd = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)
    thc = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)
    cbg = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)
    rating = models.DecimalField(max_digits=3, decimal_places=1)
    img = models.ImageField(upload_to='strains/images', blank=True, null=True)
    img_alt_text = models.CharField(max_length=255, blank=True, null=True)
    category = models.CharField(max_length=10, choices=CATEGORY_CHOICES)
    feelings = models.ManyToManyField('Feeling')
    negatives = models.ManyToManyField('Negative')
    helps_with = models.ManyToManyField('HelpsWith')
    flavors = models.ManyToManyField('Flavor')
    dominant_terpene = models.ForeignKey('Terpene', related_name='dominant_in_strains', null=True,
                                         blank=True, on_delete=models.SET_NULL)
    other_terpenes = models.ManyToManyField('Terpene', related_name='in_strains', blank=True)
    slug = models.SlugField(unique=True, default='')
    active = models.BooleanField(default=False)
    top = models.BooleanField(default=False)
    main = models.BooleanField(default=False)
    is_review = models.BooleanField(default=False)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    @property
    def structured_data(self):
        data = {
            '@type': 'Product',
            'name': self.name,
            'description': self.description,
            'image': self.img.url if self.img else None,
            'category': self.get_category_display(),
            'feelings': [feeling.name for feeling in self.feelings.all()],
            'negatives': [negative.name for negative in self.negatives.all()],
            'helpsWith': [helps_with.name for helps_with in self.helps_with.all()],
            'flavors': [flavor.name for flavor in self.flavors.all()],
        }
        return data

    def __str__(self):
        return self.name


class AlternativeStrainName(models.Model):
    name = models.CharField(max_length=255)
    strain = models.ForeignKey(Strain, related_name='alternative_names', on_delete=models.CASCADE)

    def __str__(self):
        return self.name


class Article(BaseText):
    category = models.ManyToManyField('ArticleCategory')
    slug = models.SlugField(unique=True, default='', blank=True, max_length=255)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)


class ArticleImage(models.Model):
    article = models.ForeignKey(Article, on_delete=models.CASCADE, related_name='images')
    img = models.ImageField(upload_to='articles/images/')
    img_alt_text = models.CharField(max_length=255, blank=True, null=True)
    is_preview = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.article.title} - {self.img_alt_text}"


class ArticleCategory(models.Model):
    name = models.CharField(max_length=50, unique=True)

    def __str__(self):
        return self.name


class Feeling(models.Model):
    name = models.CharField(max_length=50, unique=True)

    def __str__(self):
        return self.name


class Negative(models.Model):
    name = models.CharField(max_length=50, unique=True)

    def __str__(self):
        return self.name


class HelpsWith(models.Model):
    name = models.CharField(max_length=50, unique=True)

    def __str__(self):
        return self.name


class Flavor(models.Model):
    name = models.CharField(max_length=50, unique=True)

    def __str__(self):
        return self.name


class Terpene(models.Model):
    name = models.CharField(max_length=50, unique=True)
    description = models.TextField(blank=True)

    def __str__(self):
        return self.name


@receiver(post_delete, sender=Strain)
def delete_strain_image(sender, instance, **kwargs):
    if instance.img:
        instance.img.delete(False)


@receiver(post_delete, sender=ArticleImage)
def delete_article_image(sender, instance, **kwargs):
    if instance.img:
        instance.img.delete(False)
