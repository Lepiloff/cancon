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

        Returns URLs with structure:
        {
            'location': 'https://cannament.com/strain/northern-lights/',
            'lastmod': datetime(...),
            'alternates': [
                {'language': 'es', 'location': 'https://...'},
                {'language': 'en', 'location': 'https://...'},
            ]
        }
        """
        urls = []
        latest_lastmod = None
        all_items_lastmod = True

        # Get all items once
        items = self.items()

        for item in items:
            # Generate URLs for all languages
            loc_alternates = []
            primary_url = None

            for lang in self.languages:
                with translation.override(lang):
                    # Use reverse() in language context
                    loc = self._location(item, force_lang=lang)
                    loc_full = self._get_full_url(loc)

                    loc_alternates.append({
                        'language': lang,
                        'location': loc_full,
                    })

                    # Primary URL is Spanish (default)
                    if lang == 'es':
                        primary_url = loc_full

            # Get lastmod
            lastmod = self.lastmod(item)
            if all_items_lastmod:
                all_items_lastmod = lastmod is not None
                if lastmod and (latest_lastmod is None or lastmod > latest_lastmod):
                    latest_lastmod = lastmod

            # Build URL entry
            url_entry = {
                'item': item,
                'location': primary_url,
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
        return Article.objects.all().order_by('-id')

    def lastmod(self, obj):
        return obj.updated_at if hasattr(obj, 'updated_at') else None

    def _location(self, obj, force_lang=None):
        return reverse('article_detail', kwargs={'slug': obj.slug})
