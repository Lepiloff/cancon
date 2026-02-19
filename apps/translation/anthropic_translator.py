"""
Anthropic (Claude) Translator Implementation

Drop-in replacement for OpenAITranslator using Claude API.
"""

import json
import logging
from typing import Dict

import anthropic

from .base_translator import (
    BaseTranslator,
    TranslationAPIError,
    TranslationParseError,
)
from .config import TranslationConfig
from .prompts import TranslationPrompts

logger = logging.getLogger(__name__)


class AnthropicTranslator(BaseTranslator):
    """Anthropic Claude-based translator implementation."""

    def __init__(self):
        if not TranslationConfig.ANTHROPIC_API_KEY:
            raise ValueError(
                "ANTHROPIC_API_KEY environment variable is not set. "
                "Please add it to your .env file."
            )
        self.client = anthropic.Anthropic(
            api_key=TranslationConfig.ANTHROPIC_API_KEY,
            timeout=TranslationConfig.OPENAI_TIMEOUT,
        )
        self.model = TranslationConfig.ANTHROPIC_MODEL
        self.temperature = TranslationConfig.OPENAI_TEMPERATURE
        self.max_tokens = TranslationConfig.OPENAI_MAX_TOKENS

    def translate(
        self,
        model_name: str,
        fields: Dict[str, str],
        source_lang: str,
        target_lang: str,
    ) -> Dict[str, str]:
        if not fields:
            return {}

        content = None
        try:
            system_prompt = TranslationPrompts.get_system_prompt(
                model_name, source_lang, target_lang
            )
            user_prompt = TranslationPrompts.format_user_prompt(fields)

            logger.info(
                f"Translating {model_name} fields: {list(fields.keys())} "
                f"from {source_lang} to {target_lang} [Claude]"
            )

            response = self.client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                system=system_prompt,
                messages=[
                    {"role": "user", "content": user_prompt},
                ],
            )

            content = response.content[0].text.strip()

            # Remove markdown code blocks if present
            if content.startswith('```'):
                lines = content.split('\n')
                lines = lines[1:]
                if lines and lines[-1].strip() == '```':
                    lines = lines[:-1]
                content = '\n'.join(lines).strip()

            translations = json.loads(content)

            logger.info(
                f"Successfully translated {len(translations)} fields for {model_name} [Claude]"
            )
            return translations

        except anthropic.APIError as e:
            error_msg = f"Anthropic API error: {str(e)}"
            logger.error(error_msg)
            raise TranslationAPIError(error_msg) from e

        except json.JSONDecodeError as e:
            error_msg = f"Failed to parse Claude response as JSON: {str(e)}"
            logger.error(f"{error_msg}\nResponse content: {content}")
            raise TranslationParseError(error_msg) from e

        except Exception as e:
            error_msg = f"Unexpected error during translation: {str(e)}"
            logger.error(error_msg)
            raise TranslationAPIError(error_msg) from e

    def validate_connection(self) -> bool:
        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=5,
                messages=[
                    {"role": "user", "content": "Hello"}
                ],
            )
            return bool(response.content)
        except Exception as e:
            logger.error(f"Anthropic connection validation failed: {str(e)}")
            return False
