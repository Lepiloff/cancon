from django import template
from django.utils import translation

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
