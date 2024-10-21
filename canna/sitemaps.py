# apps/strains/sitemaps.py

from django.contrib.sitemaps import Sitemap
from django.urls import reverse
from apps.strains.models import Strain, Article

class StrainSitemap(Sitemap):
    changefreq = "weekly"
    priority = 0.8

    def items(self):
        return Strain.objects.filter(active=True)

    def location(self, obj):
        return reverse('strain_detail', args=[obj.slug])

class ArticleSitemap(Sitemap):
    changefreq = "weekly"
    priority = 0.6

    def items(self):
        return Article.objects.all()

    def location(self, obj):
        return reverse('article_detail', args=[obj.slug])
