import re

from django import template
from django.conf import settings
from django.utils.safestring import mark_safe

register = template.Library()

# Matches <a href="/strain/slug/"> or <a href="/en/strain/slug/">
_STRAIN_LINK_RE = re.compile(
    r'<a\b([^>]*href=["\'](?:/(?:en/)?strain/([\w-]+)/)["\'][^>]*)>(.*?)</a>',
    re.IGNORECASE | re.DOTALL,
)


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


@register.filter
def absolute_url(path):
    """
    Build a stable absolute URL for SEO tags from SITE_PROTOCOL + SITE_DOMAIN.
    """
    protocol = getattr(settings, 'SITE_PROTOCOL', 'https')
    domain = getattr(settings, 'SITE_DOMAIN', 'cannamente.com')
    base = f'{protocol}://{domain}'.rstrip('/')

    if not path:
        return f'{base}/'

    value = str(path).strip()
    if value.startswith('http://') or value.startswith('https://'):
        return value

    if not value.startswith('/'):
        value = f'/{value}'

    return f'{base}{value}'


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

    # Use request.path (without query string) for clean hreflang URLs
    current_path = request.path
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


@register.filter
def deactivate_strain_links(html):
    """
    Replace <a> links to inactive strains with plain <span> tags.

    Parses all strain links in the HTML, checks which slugs are active
    in one DB query, and replaces inactive ones with styled spans.
    """
    if not html:
        return html

    text = str(html)
    matches = list(_STRAIN_LINK_RE.finditer(text))
    if not matches:
        return html

    # Collect unique slugs from all matches
    slugs = {m.group(2) for m in matches}

    # Single DB query: get set of active slugs
    from apps.strains.models import Strain
    active_slugs = set(
        Strain.objects.filter(slug__in=slugs, active=True)
        .values_list('slug', flat=True)
    )

    def _replace(match):
        slug = match.group(2)
        if slug in active_slugs:
            return match.group(0)  # keep link as-is
        link_text = match.group(3)
        return f'<span class="strain-link-inactive">{link_text}</span>'

    result = _STRAIN_LINK_RE.sub(_replace, text)
    return mark_safe(result)
