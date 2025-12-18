"""
Middleware for language URL management.

Ensures that language and URL prefix are always consistent:
- EN language → must be on /en/ path
- ES language → must be on path without /en/
- Admin panel → always English (regardless of LANGUAGE_CODE)
"""

from django.shortcuts import redirect
from django.utils import translation
from django.conf import settings
import logging
import geoip2.database


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


class GeoLanguageMiddleware:
    """
    Automatically detect user's preferred language based on their IP address geolocation.

    This middleware runs BEFORE LocaleMiddleware to set up the language preference.
    It respects manual language selection (URL prefix or cookies) and only acts
    when no explicit language choice has been made.

    Priority (highest to lowest):
    1. URL prefix (/en/ or no prefix for ES)
    2. django_language cookie/session
    3. Geolocation-based detection (this middleware)
    4. LANGUAGE_CODE setting fallback
    """

    def __init__(self, get_response):
        self.get_response = get_response
        self.country_language_map = getattr(settings, 'COUNTRY_LANGUAGE_MAP', {})
        self.fallback_language = getattr(settings, 'FALLBACK_LANGUAGE', 'en')

    def __call__(self, request):
        logger = logging.getLogger(__name__)

        # Skip for admin, static files, etc.
        if self._should_skip(request.path):
            return self.get_response(request)

        # Only set language if not already explicitly chosen
        has_explicit = self._has_explicit_language(request)

        if not has_explicit:
            detected_language = self._get_language_by_geo(request)
            if detected_language:
                self._set_language_preference(request, detected_language)

                # Redirect to correct URL prefix based on detected language
                if detected_language == 'en' and not (request.path.startswith('/en/') or request.path == '/en'):
                    # English detected but on Spanish URL → redirect to /en/
                    new_url = f'/en{request.path}'
                    return redirect(new_url, permanent=False)

                elif detected_language == 'es' and (request.path.startswith('/en/') or request.path == '/en'):
                    # Spanish detected but on English URL → redirect to Spanish URL
                    new_url = request.path[3:] if request.path.startswith('/en/') else '/'
                    new_url = new_url or '/'  # Ensure we don't get empty string
                    return redirect(new_url, permanent=False)

        return self.get_response(request)

    def _should_skip(self, path):
        """Skip certain paths that don't need language detection"""
        skip_prefixes = [
            '/admin/',
            '/i18n/',
            '/static/',
            '/media/',
            '/tinymce/',
            '/robots.txt',
            '/favicon.ico',
            '/sitemap.xml',
        ]
        return any(path.startswith(prefix) for prefix in skip_prefixes)

    def _has_explicit_language(self, request):
        """
        Check if user has already made an explicit language choice.

        Returns True if:
        - URL has /en/ prefix (English choice)
        - django_language cookie exists
        - django_language session key exists
        """
        # Check URL prefix
        path = request.path
        if path.startswith('/en/') or path == '/en':
            return True

        # Check cookie
        if 'django_language' in request.COOKIES:
            return True

        # Check session
        if hasattr(request, 'session') and 'django_language' in request.session:
            return True

        return False

    def _get_language_by_geo(self, request):
        """
        Determine language based on user's IP address geolocation.

        Returns language code (es/en) or None if detection fails.
        """
        logger = logging.getLogger(__name__)

        try:
            # Get client IP
            client_ip = self._get_client_ip(request)
            if not client_ip:
                return None

            # Check for CDN/Load Balancer headers first (more reliable)
            country_code = self._get_country_from_headers(request)

            # Fallback to GeoIP2 if no CDN headers
            if not country_code:
                country_code = self._get_country_from_geoip(client_ip)

            if country_code:
                # Look up language for this country
                detected_language = self.country_language_map.get(
                    country_code.upper(),
                    self.fallback_language
                )

                # Store detected info for debugging/analytics
                request.detected_country = country_code
                request.detected_language = detected_language

                return detected_language

        except Exception as e:
            # Log error but don't break the site
            logger.warning(f"GeoLanguageMiddleware error: {e}")

        return None

    def _get_client_ip(self, request):
        """Extract client IP from request headers"""
        # Check common proxy headers
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0].strip()

        x_real_ip = request.META.get('HTTP_X_REAL_IP')
        if x_real_ip:
            return x_real_ip.strip()

        return request.META.get('REMOTE_ADDR')

    def _get_country_from_headers(self, request):
        """
        Check for country code in CDN/ALB headers.
        These are more reliable than GeoIP when available.
        """
        # Cloudflare
        cf_country = request.META.get('HTTP_CF_IPCOUNTRY')
        if cf_country and cf_country != 'XX':  # XX = unknown
            return cf_country

        # AWS ALB or other load balancers
        country_header = request.META.get('HTTP_X_COUNTRY_CODE')
        if country_header:
            return country_header

        return None

    def _get_country_from_geoip(self, ip_address):
        """Get country from GeoIP2 database using direct geoip2 import"""
        try:
            geoip_path = getattr(settings, 'GEOIP_PATH', None)
            if not geoip_path:
                return None

            database_path = f"{geoip_path}/GeoLite2-Country.mmdb"

            with geoip2.database.Reader(database_path) as reader:
                response = reader.country(ip_address)
                return response.country.iso_code
        except Exception:
            return None

    def _set_language_preference(self, request, language_code):
        """
        Set language preference in session for LocaleMiddleware to pick up.

        We don't call translation.activate() here because LocaleMiddleware
        will handle that. We just set the preference.
        """
        logger = logging.getLogger(__name__)

        # Ensure it's a valid language
        available_languages = [lang[0] for lang in settings.LANGUAGES]
        if language_code not in available_languages:
            logger.warning(f"Invalid language {language_code}, using fallback: {self.fallback_language}")
            language_code = self.fallback_language

        # Set in session for LocaleMiddleware (use the standard Django key)
        language_session_key = 'django_language'
        if hasattr(request, 'session'):
            request.session[language_session_key] = language_code
