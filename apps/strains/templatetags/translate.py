from django import template
from django.conf import settings
from django.utils.translation import get_language

register = template.Library()


@register.filter
def translate(value, translations_dict=None):
    """
    Deprecated: This filter is kept for backward compatibility.
    With django-modeltranslation, translations are now stored in the database.

    Simply returns the value as-is since modeltranslation handles language switching automatically.
    When a proper language switcher is implemented, Django's translation.get_language() will
    determine which field (_en or _es) to return.
    """
    # Return value as-is - modeltranslation handles the language switching
    return value


@register.simple_tag(takes_context=True)
def alt_url(context, lang_code):
    """
    Generate URL for the current page in a different language.

    Uses Django's i18n system to properly handle:
    - i18n_patterns prefixes (e.g., /en/)
    - Query parameters
    - SCRIPT_NAME and deployment subdirectories
    - Any number of languages without hardcoded logic

    Usage in templates:
        {% load translate %}
        {% alt_url 'en' %}  → translates current URL to English
        {% alt_url 'es' %}  → translates current URL to Spanish

    Example:
        Current URL: /strain/northern-lights/
        {% alt_url 'en' %} → /en/strain/northern-lights/

        Current URL: /en/strain/northern-lights/
        {% alt_url 'es' %} → /strain/northern-lights/
    """

    request = context.get('request')
    if not request:
        return ''

    # Get current path with query string
    current_path = request.get_full_path()
    current_lang = get_language()

    # Remove current language prefix if present
    path_without_lang = current_path
    for lang, _ in settings.LANGUAGES:
        prefix = f'/{lang}/'
        if current_path.startswith(prefix):
            path_without_lang = current_path[len(f'/{lang}'):]
            break

    # Add target language prefix (only if not Spanish, which is default)
    if lang_code == 'es' or lang_code == settings.LANGUAGE_CODE:
        # Spanish is default - no prefix
        return path_without_lang
    else:
        # Other languages get prefix
        return f'/{lang_code}{path_without_lang}'
