"""
OpenAI Translator Implementation

Single Responsibility: Handles OpenAI API communication for translations.
Compatible with openai>=2.0.0
"""

import json
import logging
from typing import Dict

from openai import OpenAI
from openai import OpenAIError, APIError, APIConnectionError, RateLimitError

from .base_translator import (
    BaseTranslator,
    TranslationAPIError,
    TranslationParseError,
)
from .config import TranslationConfig
from .prompts import TranslationPrompts

logger = logging.getLogger(__name__)


class OpenAITranslator(BaseTranslator):
    """OpenAI-based translator implementation (compatible with openai>=2.0.0)."""

    def __init__(self):
        """Initialize OpenAI translator."""
        TranslationConfig.validate()
        self.client = OpenAI(
            api_key=TranslationConfig.OPENAI_API_KEY,
            timeout=TranslationConfig.OPENAI_TIMEOUT,
        )
        self.model = TranslationConfig.OPENAI_MODEL
        self.temperature = TranslationConfig.OPENAI_TEMPERATURE
        self.max_tokens = TranslationConfig.OPENAI_MAX_TOKENS

    def translate(
        self,
        model_name: str,
        fields: Dict[str, str],
        source_lang: str,
        target_lang: str,
    ) -> Dict[str, str]:
        """
        Translate fields using OpenAI API.

        Args:
            model_name: Model name (Strain, Article, Terpene)
            fields: Dictionary of field_name: content_to_translate
            source_lang: Source language code (en, es)
            target_lang: Target language code (en, es)

        Returns:
            Dictionary of field_name: translated_content

        Raises:
            TranslationAPIError: If API call fails
            TranslationParseError: If response parsing fails
        """
        if not fields:
            return {}

        try:
            # Generate prompts
            system_prompt = TranslationPrompts.get_system_prompt(
                model_name, source_lang, target_lang
            )
            user_prompt = TranslationPrompts.format_user_prompt(fields)

            logger.info(
                f"Translating {model_name} fields: {list(fields.keys())} "
                f"from {source_lang} to {target_lang}"
            )

            # Call OpenAI API
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=self.temperature,
                max_tokens=self.max_tokens,
            )

            # Extract and parse response
            content = response.choices[0].message.content.strip()

            # Remove markdown code blocks if present
            if content.startswith('```'):
                lines = content.split('\n')
                # Remove first line (```json or ```)
                lines = lines[1:]
                # Remove last line (```)
                if lines and lines[-1].strip() == '```':
                    lines = lines[:-1]
                content = '\n'.join(lines).strip()

            translations = json.loads(content)

            logger.info(
                f"Successfully translated {len(translations)} fields for {model_name}"
            )

            return translations

        except OpenAIError as e:
            error_msg = f"OpenAI API error: {str(e)}"
            logger.error(error_msg)
            raise TranslationAPIError(error_msg) from e

        except json.JSONDecodeError as e:
            error_msg = f"Failed to parse OpenAI response as JSON: {str(e)}"
            logger.error(f"{error_msg}\nResponse content: {content}")
            raise TranslationParseError(error_msg) from e

        except Exception as e:
            error_msg = f"Unexpected error during translation: {str(e)}"
            logger.error(error_msg)
            raise TranslationAPIError(error_msg) from e

    def validate_connection(self) -> bool:
        """
        Validate OpenAI API connection.

        Returns:
            True if connection is valid, False otherwise
        """
        try:
            # Simple test with minimal tokens
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "user", "content": "Hello"}
                ],
                max_tokens=5,
            )
            return bool(response.choices)
        except Exception as e:
            logger.error(f"OpenAI connection validation failed: {str(e)}")
            return False
