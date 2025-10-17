"""
Translation Service Application

Provides AI-powered translation services using OpenAI API.
"""

from .openai_translator import OpenAITranslator
from .config import TranslationConfig

__all__ = ['OpenAITranslator', 'TranslationConfig']
