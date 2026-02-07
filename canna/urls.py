"""
URL configuration for canna project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.conf import settings
from django.conf.urls.static import static
from django.conf.urls.i18n import i18n_patterns
from django.contrib import admin
from django.contrib.sitemaps.views import sitemap
from django.views.i18n import JavaScriptCatalog
from django.urls import path, include

from canna.sitemaps import StrainSitemap, ArticleSitemap
from canna.views import robots_txt


sitemaps = {
    'strains': StrainSitemap(),
    'articles': ArticleSitemap(),
}


handler404 = 'apps.strains.views.custom_page_not_found_view'

# URLs that DON'T need language prefix
urlpatterns = [
    path('manage-canna/', admin.site.urls),
    path('tinymce/', include('tinymce.urls')),
    path('i18n/', include('django.conf.urls.i18n')),  # Language switcher endpoint
    path('robots.txt', robots_txt, name='robots_txt'),  # SEO: robots.txt
    path('sitemap.xml', sitemap, {
        'sitemaps': sitemaps,
        'template_name': 'sitemap.xml',  # Custom template with hreflang support
    }, name='django.contrib.sitemaps.views.sitemap'),
]

# Multi-language URLs with i18n_patterns
# ES (default): /strain/... - NO prefix (preserves existing SEO!)
# EN (new):     /en/strain/... - WITH /en/ prefix
urlpatterns += i18n_patterns(
    path('jsi18n/', JavaScriptCatalog.as_view(domain='django'), name='javascript-catalog'),
    path('', include('apps.strains.urls')),
    path('store/', include('apps.store.urls')),
    path('api/chat/', include('apps.chat_bot.urls')),
    prefix_default_language=False,  # Spanish WITHOUT prefix - CRITICAL for SEO!
)

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
