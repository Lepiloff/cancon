from abc import ABC, abstractmethod
from typing import Dict


class BaseTranslator(ABC):
    """Abstract base class for translation services."""

    @abstractmethod
    def translate(
        self,
        model_name: str,
        fields: Dict[str, str],
        source_lang: str,
        target_lang: str,
    ) -> Dict[str, str]:
        """
        Translate fields from source language to target language.

        Args:
            model_name: Model name (Strain, Article, Terpene)
            fields: Dictionary of field_name: content_to_translate
            source_lang: Source language code (en, es)
            target_lang: Target language code (en, es)

        Returns:
            Dictionary of field_name: translated_content

        Raises:
            TranslationError: If translation fails
        """
        pass

    @abstractmethod
    def validate_connection(self) -> bool:
        """
        Validate that the translation service is accessible.

        Returns:
            True if connection is valid, False otherwise
        """
        pass


class TranslationError(Exception):
    """Base exception for translation errors."""
    pass


class TranslationAPIError(TranslationError):
    """Exception raised when API call fails."""
    pass


class TranslationParseError(TranslationError):
    """Exception raised when response parsing fails."""
    pass
