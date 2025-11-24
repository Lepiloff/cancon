"""
Context processors for making settings available in templates.
"""
from django.conf import settings


def chat_settings(request):
    """
    Make AI chat settings available in all templates.
    """
    return {
        'ENABLE_AI_CHAT': settings.ENABLE_AI_CHAT,
    }

