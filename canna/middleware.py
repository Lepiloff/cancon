"""
Middleware for language URL management.

Ensures that language and URL prefix are always consistent:
- EN language → must be on /en/ path
- ES language → must be on path without /en/
- Admin panel → always English (regardless of LANGUAGE_CODE)
"""

from django.shortcuts import redirect
from django.utils import translation


class AdminEnglishMiddleware:
    """
    Force English language for Django admin panel.

    This middleware ensures the admin interface is always in English,
    regardless of the default LANGUAGE_CODE setting or user preferences.

    IMPORTANT: Must be placed AFTER LocaleMiddleware in MIDDLEWARE settings.
    This allows LocaleMiddleware to run first, then we override for admin.

    Why this is needed:
    - Frontend default language: Spanish (LANGUAGE_CODE='es')
    - Admin interface language: English (better for developers/admins)
    - Keeps URLs SEO-friendly (Spanish without /es/ prefix)
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Force English for admin panel
        if request.path.startswith('/admin/'):
            translation.activate('en')
            request.LANGUAGE_CODE = 'en'

        response = self.get_response(request)

        # Ensure response has English set for admin
        # (in case view code changed language during request processing)
        if request.path.startswith('/admin/'):
            translation.activate('en')

        return response


class LanguageUrlRedirectMiddleware:
    """
    Redirect to ensure language matches URL prefix.

    This middleware prevents confusion when:
    1. User has EN in session/cookie but visits ES URL → redirect to /en/
    2. User has ES in session/cookie but visits EN URL → redirect to ES URL

    This is critical for:
    - SEO: Each URL should always serve the same language
    - Cache: Prevent mixed language caching
    - User experience: URL clearly indicates language
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Normalize language like 'en-us' -> 'en'
        current_lang = (translation.get_language() or '').split('-')[0]
        path = request.path

        # Skip for non-multilingual URLs
        if self._should_skip(path):
            return self.get_response(request)

        # EN language but on ES path (without /en/) → redirect to /en/
        if current_lang == 'en' and not (path == '/en' or path.startswith('/en/')):
            return redirect(f'/en{path}', permanent=True)

        # ES language but on EN path (with /en/) → redirect to ES path
        if current_lang == 'es' and (path == '/en' or path.startswith('/en/')):
            # Remove '/en' prefix
            new_path = path[3:] or '/'
            return redirect(new_path, permanent=True)

        return self.get_response(request)

    def _should_skip(self, path):
        """
        Check if URL should skip language redirect.

        Skip for:
        - Admin panel
        - i18n endpoint (language switcher)
        - Static files
        - Media files
        - Tinymce
        """
        skip_prefixes = [
            '/admin/',
            '/i18n/',
            '/static/',
            '/media/',
            '/tinymce/',
            '/robots.txt',
            '/favicon.ico',
        ]

        return any(path.startswith(prefix) for prefix in skip_prefixes)
