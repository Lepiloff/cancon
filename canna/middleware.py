"""
Middleware for language URL management, cookie consent, and banner state.

Ensures that language and URL prefix are always consistent:
- EN language → must be on /en/ path
- ES language → must be on path without /en/
- Admin panel → always English (regardless of LANGUAGE_CODE)

Also handles restoring cookie consent on login and the anonymous registration banner funnel.
"""

import json
from urllib.parse import urlparse

from django.shortcuts import redirect
from django.utils import translation
from django.conf import settings
import logging
import geoip2.database

from canna.context_processors import cookie_consent
from canna.views import (
    COOKIE_CONSENT_MAX_AGE,
    REGISTRATION_BANNER_DISMISS_COOKIE,
)


REGISTRATION_BANNER_ARMED_SESSION_KEY = '_reg_banner_armed'
REGISTRATION_BANNER_ENTRY_PATH_SESSION_KEY = '_reg_banner_entry_path'
REGISTRATION_BANNER_ENTRY_SOURCE_SESSION_KEY = '_reg_banner_entry_source'
REGISTRATION_BANNER_CONSUMED_SESSION_KEY = '_reg_banner_consumed'

SEARCH_ENGINE_MARKERS = (
    'google.',
    'bing.',
    'search.yahoo.',
    'duckduckgo.',
    'yandex.',
    'ecosia.',
    'search.brave.',
    'startpage.',
)


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
        if request.path.startswith('/manage-canna/'):
            translation.activate('en')
            request.LANGUAGE_CODE = 'en'

        response = self.get_response(request)

        # Ensure response has English set for admin
        # (in case view code changed language during request processing)
        if request.path.startswith('/manage-canna/'):
            translation.activate('en')

        return response


class LanguageUrlRedirectMiddleware:
    """
    Ensure URL prefix is the single source of truth for language.

    Instead of redirecting based on session/cookie/Accept-Language,
    this middleware FORCES the language to match the URL:
    - /en/... path → activate English
    - path without /en/ → activate Spanish (default)

    No redirects are issued. The URL determines the language, period.
    This prevents search engine bots from being redirected away from
    canonical Spanish URLs due to Accept-Language: en headers.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        path = request.path

        # Skip for non-multilingual URLs
        if self._should_skip(path):
            return self.get_response(request)

        # URL is the source of truth for language
        if path == '/en' or path.startswith('/en/'):
            # /en/ prefix → English
            if translation.get_language() != 'en':
                translation.activate('en')
                request.LANGUAGE_CODE = 'en'
        else:
            # No prefix → Spanish (default)
            if translation.get_language() != 'es':
                translation.activate('es')
                request.LANGUAGE_CODE = 'es'

        return self.get_response(request)

    def _should_skip(self, path):
        skip_prefixes = [
            '/manage-canna/',
            '/api/',
            '/i18n/',
            '/static/',
            '/media/',
            '/tinymce/',
            '/robots.txt',
            '/favicon.ico',
            '/sitemap.xml',
            '/cookie-consent/',
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

    # Search engine bots that must crawl both language versions freely
    BOT_USER_AGENTS = [
        'googlebot', 'bingbot', 'yandexbot', 'baiduspider',
        'duckduckbot', 'slurp', 'applebot', 'petalbot',
        'semrushbot', 'ahrefsbot', 'mj12bot',
    ]

    def __call__(self, request):
        logger = logging.getLogger(__name__)

        # Skip for admin, static files, etc.
        if self._should_skip(request.path):
            return self.get_response(request)

        # Skip for search engine bots — let them crawl both language versions
        if self._is_bot(request):
            return self.get_response(request)

        # Only set language if not already explicitly chosen
        has_explicit = self._has_explicit_language(request)

        if not has_explicit:
            detected_language = self._get_language_by_geo(request)
            if detected_language:
                # Only save preference in session — do NOT redirect.
                # The URL is the source of truth for language.
                # User can switch language manually via the language switcher.
                self._set_language_preference(request, detected_language)

        return self.get_response(request)

    def _is_bot(self, request):
        """Check if request comes from a search engine bot."""
        ua = request.META.get('HTTP_USER_AGENT', '').lower()
        return any(bot in ua for bot in self.BOT_USER_AGENTS)

    def _should_skip(self, path):
        """Skip certain paths that don't need language detection"""
        skip_prefixes = [
            '/manage-canna/',
            '/api/',
            '/i18n/',
            '/static/',
            '/media/',
            '/tinymce/',
            '/robots.txt',
            '/favicon.ico',
            '/sitemap.xml',
            '/cookie-consent/',
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


class CookieConsentMiddleware:
    """
    Restore cookie consent cookie after login.

    When a user logs in, the login signal stores their saved consent
    preferences in the session under '_restore_cookie_consent'. This
    middleware detects that flag and sets the cookie on the response,
    so the user doesn't see the consent banner again.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        # Check if we need to restore the cookie consent cookie
        if hasattr(request, 'session') and '_restore_cookie_consent' in request.session:
            consent = request.session.pop('_restore_cookie_consent')
            response.set_cookie(
                'cookie_consent',
                json.dumps(consent),
                max_age=COOKIE_CONSENT_MAX_AGE,
                samesite='Lax',
                path='/',
                httponly=False,
            )

        return response


class RegistrationBannerMiddleware:
    """
    Track anonymous entry funnel and decide whether to show the signup banner.

    Flow:
    - qualifying first visit from direct/search/external arms the funnel
    - first internal navigation to another public page shows the banner
    - cookie-consent visibility suppresses display but does not destroy the funnel
    - dismiss cooldown cookie suppresses the funnel entirely
    """

    EXCLUDED_PREFIXES = (
        '/api/',
        '/manage-canna/',
        '/tinymce/',
        '/i18n/',
        '/jsi18n/',
        '/cookie-consent/',
        '/registration-banner-dismiss/',
        '/robots.txt',
        '/sitemap.xml',
    )

    EXCLUDED_FIRST_SEGMENTS = {
        'accounts',
        'manage-canna',
        'api',
        'tinymce',
        'i18n',
        'jsi18n',
    }

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request._show_registration_banner = False
        self._prepare_registration_banner_state(request)
        return self.get_response(request)

    def _prepare_registration_banner_state(self, request):
        if not hasattr(request, 'session'):
            return

        if getattr(request, 'user', None) and request.user.is_authenticated:
            self._clear_funnel_state(request)
            return

        if not self._is_eligible_request(request):
            return

        if request.COOKIES.get(REGISTRATION_BANNER_DISMISS_COOKIE):
            self._clear_funnel_state(request)
            return

        if request.session.get(REGISTRATION_BANNER_CONSUMED_SESSION_KEY):
            return

        current_path = request.path_info or '/'
        source = self._classify_source(request)

        if (
            request.session.get(REGISTRATION_BANNER_ARMED_SESSION_KEY)
            and self._is_internal_navigation(request, current_path)
            and self._cookie_banner_hidden(request)
        ):
            request._show_registration_banner = True
            self._consume_funnel(request)
            return

        if source in {'direct', 'search', 'external'}:
            request.session[REGISTRATION_BANNER_ARMED_SESSION_KEY] = True
            request.session[REGISTRATION_BANNER_ENTRY_PATH_SESSION_KEY] = current_path
            request.session[REGISTRATION_BANNER_ENTRY_SOURCE_SESSION_KEY] = source

    def _is_eligible_request(self, request):
        if request.method != 'GET':
            return False

        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return False

        return self._is_public_page_path(request.path_info or '/')

    def _is_public_page_path(self, path):
        if not path.startswith('/'):
            path = f'/{path}'

        for prefix in self.EXCLUDED_PREFIXES:
            if path.startswith(prefix):
                return False

        path_without_lang = path
        if path_without_lang.startswith('/en/'):
            path_without_lang = path_without_lang[3:]
        elif path_without_lang == '/en':
            path_without_lang = '/'

        first_segment = path_without_lang.strip('/').split('/', 1)[0]
        if first_segment in self.EXCLUDED_FIRST_SEGMENTS:
            return False

        return True

    def _cookie_banner_hidden(self, request):
        return not cookie_consent(request)['show_cookie_banner']

    def _classify_source(self, request):
        referrer = request.META.get('HTTP_REFERER', '')
        if not referrer:
            return 'direct'

        parsed = urlparse(referrer)
        referrer_host = (parsed.hostname or '').lower()
        current_host = request.get_host().split(':', 1)[0].lower()

        if not referrer_host:
            return 'direct'

        if referrer_host == current_host:
            return 'internal'

        for marker in SEARCH_ENGINE_MARKERS:
            if marker in referrer_host:
                return 'search'

        return 'external'

    def _is_internal_navigation(self, request, current_path):
        if self._classify_source(request) != 'internal':
            return False

        entry_path = request.session.get(REGISTRATION_BANNER_ENTRY_PATH_SESSION_KEY)
        return bool(entry_path and entry_path != current_path)

    def _consume_funnel(self, request):
        request.session[REGISTRATION_BANNER_CONSUMED_SESSION_KEY] = True
        request.session.pop(REGISTRATION_BANNER_ARMED_SESSION_KEY, None)
        request.session.pop(REGISTRATION_BANNER_ENTRY_PATH_SESSION_KEY, None)
        request.session.pop(REGISTRATION_BANNER_ENTRY_SOURCE_SESSION_KEY, None)

    def _clear_funnel_state(self, request):
        request.session.pop(REGISTRATION_BANNER_ARMED_SESSION_KEY, None)
        request.session.pop(REGISTRATION_BANNER_ENTRY_PATH_SESSION_KEY, None)
        request.session.pop(REGISTRATION_BANNER_ENTRY_SOURCE_SESSION_KEY, None)
        request.session.pop(REGISTRATION_BANNER_CONSUMED_SESSION_KEY, None)
