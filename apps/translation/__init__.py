"""
Translation Service Application

Provides AI-powered translation services using OpenAI or Anthropic API.
"""

from .openai_translator import OpenAITranslator
from .config import TranslationConfig


def get_translator():
    """Factory: return the translator matching LLM_PROVIDER env var."""
    if TranslationConfig.LLM_PROVIDER == 'anthropic':
        from .anthropic_translator import AnthropicTranslator
        return AnthropicTranslator()
    return OpenAITranslator()


__all__ = ['OpenAITranslator', 'TranslationConfig', 'get_translator']
