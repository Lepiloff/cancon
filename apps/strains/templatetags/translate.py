from django import template

register = template.Library()


@register.filter
def translate(value, translations_dict):
    return translations_dict.get(value, value)
