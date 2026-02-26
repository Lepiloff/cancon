"""
Multi-language sitemaps with hreflang support.

Generates sitemaps with bidirectional hreflang links for SEO.
Each URL entry includes alternates for ES and EN versions.
"""

from django.contrib.sitemaps import Sitemap
from django.urls import reverse
from django.utils import translation
from django.conf import settings
from apps.strains.models import Strain, Article


class I18nSitemap(Sitemap):
    """
    Base sitemap with hreflang support in XML.

    Generates entries for all languages with bidirectional hreflang links.
    This helps Google understand the relationship between language versions.
    """
    languages = ['es', 'en']
    protocol = 'https'

    def get_urls(self, page=1, site=None, protocol=None):
        """
        Override to add hreflang alternates to each URL.

        Generates a separate <url> entry for EACH language version so that
        Google treats each language version as its own canonical URL.
        Without this, Google sees only the Spanish URL as primary and marks
        English pages as "duplicate with non-matching canonical".

        Returns URLs with structure:
        {
            'location': 'https://cannamente.com/en/strain/northern-lights/',
            'lastmod': datetime(...),
            'alternates': [
                {'language': 'es', 'location': 'https://cannamente.com/strain/northern-lights/'},
                {'language': 'en', 'location': 'https://cannamente.com/en/strain/northern-lights/'},
            ]
        }
        """
        urls = []

        # Get all items once
        items = self.items()

        for item in items:
            # Build full alternates list (same for all language entries of this item)
            lang_urls = {}
            loc_alternates = []

            for lang in self.languages:
                with translation.override(lang):
                    loc = self._location(item, force_lang=lang)
                    loc_full = self._get_full_url(loc)
                    lang_urls[lang] = loc_full
                    loc_alternates.append({
                        'language': lang,
                        'location': loc_full,
                    })

            lastmod = self.lastmod(item)

            # Create a separate sitemap entry for each language version
            # so Google recognises each as a valid canonical URL
            for lang in self.languages:
                url_entry = {
                    'item': item,
                    'location': lang_urls[lang],
                    'lastmod': lastmod,
                    'changefreq': self.changefreq,
                    'priority': str(self.priority if self.priority is not None else ''),
                    'alternates': loc_alternates,
                }
                urls.append(url_entry)

        return urls

    def _location(self, obj, force_lang=None):
        """Override in subclass to generate URL via reverse()"""
        raise NotImplementedError('Subclasses must implement _location()')

    def _get_full_url(self, path):
        """Convert path to full URL"""
        # Get domain from settings or use default
        domain = getattr(settings, 'SITE_DOMAIN', 'cannamente.com')
        return f'{self.protocol}://{domain}{path}'


class StrainSitemap(I18nSitemap):
    changefreq = "weekly"
    priority = 0.9

    def items(self):
        return Strain.objects.filter(active=True).order_by('-id')

    def lastmod(self, obj):
        return obj.updated_at if hasattr(obj, 'updated_at') else None

    def _location(self, obj, force_lang=None):
        # reverse() automatically adds /en/ if needed based on translation.override()
        return reverse('strain_detail', kwargs={'slug': obj.slug})


class ArticleSitemap(I18nSitemap):
    changefreq = "weekly"
    priority = 0.8

    def items(self):
        return Article.objects.exclude(
            category__name='Terpenes'
        ).order_by('-id')

    def lastmod(self, obj):
        return obj.updated_at if hasattr(obj, 'updated_at') else None

    def _location(self, obj, force_lang=None):
        return reverse('article_detail', kwargs={'slug': obj.slug})


class TerpeneSitemap(I18nSitemap):
    changefreq = "monthly"
    priority = 0.7

    def items(self):
        return Article.objects.filter(
            category__name='Terpenes'
        ).order_by('-id')

    def lastmod(self, obj):
        return obj.updated_at if hasattr(obj, 'updated_at') else None

    def _location(self, obj, force_lang=None):
        return reverse('terpene_detail', kwargs={'slug': obj.slug})


class StaticPageSitemap(I18nSitemap):
    changefreq = "monthly"

    _pages = {
        'main_page': 1.0,
        'strain_list': 0.9,
        'article_list': 0.8,
        'terpene_list': 0.7,
    }

    def items(self):
        return list(self._pages.keys())

    def lastmod(self, obj):
        return None

    def _location(self, obj, force_lang=None):
        return reverse(obj)

    def get_priority(self, item):
        return self._pages.get(item, 0.5)

    def get_urls(self, page=1, site=None, protocol=None):
        urls = []
        items = self.items()

        for item in items:
            lang_urls = {}
            loc_alternates = []

            for lang in self.languages:
                with translation.override(lang):
                    loc = self._location(item, force_lang=lang)
                    loc_full = self._get_full_url(loc)
                    lang_urls[lang] = loc_full
                    loc_alternates.append({
                        'language': lang,
                        'location': loc_full,
                    })

            for lang in self.languages:
                url_entry = {
                    'item': item,
                    'location': lang_urls[lang],
                    'lastmod': None,
                    'changefreq': self.changefreq,
                    'priority': str(self.get_priority(item)),
                    'alternates': loc_alternates,
                }
                urls.append(url_entry)

        return urls
