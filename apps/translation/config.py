"""
Translation Configuration

Single Responsibility: Manages all translation-related configuration.
"""

import os
from typing import List, Tuple


class TranslationConfig:
    """Configuration for translation services."""

    # LLM Provider: 'openai' or 'anthropic'
    LLM_PROVIDER = os.getenv('LLM_PROVIDER', 'openai').lower()

    # OpenAI settings
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY', '')
    OPENAI_MODEL = os.getenv('OPENAI_AGENT_MODEL', 'gpt-4o-mini')
    OPENAI_TEMPERATURE = float(os.getenv('AGENT_TEMPERATURE', '0.3'))
    OPENAI_MAX_TOKENS = int(os.getenv('OPENAI_MAX_TOKENS', '4000'))
    OPENAI_TIMEOUT = int(os.getenv('OPENAI_TIMEOUT', '60'))

    # Anthropic settings
    ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY', '')
    ANTHROPIC_MODEL = os.getenv('ANTHROPIC_MODEL', 'claude-sonnet-4-20250514')

    # Rate limiting
    DEFAULT_PAUSE_SECONDS = float(os.getenv('TRANSLATION_PAUSE_SECONDS', '1.5'))

    # Supported models and their translatable fields
    TRANSLATABLE_MODELS = {
        'Strain': ['title', 'description', 'text_content', 'keywords', 'img_alt_text'],
        'Article': ['title', 'description', 'text_content', 'keywords'],
        'Terpene': ['description'],
    }

    # Language codes
    SUPPORTED_LANGUAGES = {
        'en': 'English',
        'es': 'Spanish',
    }

    # Translation directions
    VALID_DIRECTIONS = ['es-to-en', 'en-to-es']

    @classmethod
    def validate(cls) -> None:
        """Validate that all required configuration is present."""
        if cls.LLM_PROVIDER == 'anthropic':
            if not cls.ANTHROPIC_API_KEY:
                raise ValueError(
                    "ANTHROPIC_API_KEY environment variable is not set. "
                    "Please add it to your .env file."
                )
        else:
            if not cls.OPENAI_API_KEY:
                raise ValueError(
                    "OPENAI_API_KEY environment variable is not set. "
                    "Please add it to your .env file."
                )

    @classmethod
    def get_model_fields(cls, model_name: str) -> List[str]:
        """Get translatable fields for a given model."""
        return cls.TRANSLATABLE_MODELS.get(model_name, [])

    @classmethod
    def is_valid_direction(cls, direction: str) -> bool:
        """Check if translation direction is valid."""
        return direction in cls.VALID_DIRECTIONS

    @classmethod
    def parse_direction(cls, direction: str) -> Tuple[str, str]:
        """
        Parse direction string into source and target languages.

        Args:
            direction: Direction string like 'es-to-en'

        Returns:
            Tuple of (source_lang, target_lang)

        Example:
            >>> TranslationConfig.parse_direction('es-to-en')
            ('es', 'en')
        """
        if not cls.is_valid_direction(direction):
            raise ValueError(
                f"Invalid direction: {direction}. "
                f"Must be one of: {', '.join(cls.VALID_DIRECTIONS)}"
            )

        source, target = direction.split('-to-')
        return source, target
