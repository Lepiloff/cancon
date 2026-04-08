"""
Context processors for making settings available in templates.
"""
import json

from django.conf import settings


def chat_settings(request):
    """
    Make AI chat settings available in all templates.
    """
    return {
        'ENABLE_AI_CHAT': settings.ENABLE_AI_CHAT,
    }


def cookie_consent(request):
    """
    Make cookie consent state available in all templates.

    Provides:
    - cookie_consent: dict of consent preferences (empty dict if no cookie)
    - show_cookie_banner: True if user hasn't set consent yet
    - restore_cookie_consent: True if authenticated user has saved consent
      but no cookie exists (JS should restore it via POST)
    """
    raw = request.COOKIES.get('cookie_consent')
    consent = {}
    has_cookie = False

    if raw:
        try:
            consent = json.loads(raw)
            has_cookie = True
        except (json.JSONDecodeError, ValueError):
            pass

    restore = False
    if (
        not has_cookie
        and hasattr(request, 'user')
        and request.user.is_authenticated
        and request.user.cookie_consent
    ):
        restore = True
        consent = request.user.cookie_consent

    return {
        'cookie_consent': consent,
        'show_cookie_banner': not has_cookie and not restore,
        'restore_cookie_consent': restore,
    }


def registration_banner(request):
    """
    Expose registration banner state prepared by middleware.
    """
    return {
        'show_registration_banner': getattr(request, '_show_registration_banner', False),
    }
