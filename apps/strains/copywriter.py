"""
Generic copywriter service for admin-driven text generation.

Uses static prompt configuration from copywriter_config and delegates
to the OpenAI API via openai_compat.
"""

import json

from apps.strains.copywriter_config import get_config
from apps.strains.llm_output import clean_generated_output, strip_code_fences
from apps.translation.config import TranslationConfig
from apps.translation.openai_compat import create_chat_completion


# ---------------------------------------------------------------------------
# Content-type handler registry
# ---------------------------------------------------------------------------

def _get_model_class(content_type: str):
    """Lazy import to avoid circular imports."""
    from apps.strains.models import Strain, Article, Terpene
    return {'strain': Strain, 'article': Article, 'terpene': Terpene}[content_type]


def _build_strain_payload(source_text: str, obj=None) -> str:
    payload = {
        'strain_name': obj.name if obj else '',
        'description_source': source_text,
        'target_length': len(source_text),
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)


def _build_terpene_payload(source_text: str, obj=None) -> str:
    payload = {
        'terpene_name': obj.name if obj else '',
        'description_source': source_text,
        'target_length': len(source_text),
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)


def _build_article_payload(source_text: str, obj=None) -> str:
    payload = {
        'article_title': (obj.title_en or obj.title or '') if obj else '',
        'description_source': source_text,
        'target_length': len(source_text),
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)

CONTENT_TYPE_HANDLERS = {
    'strain': {
        'label': 'Strain',
        'name_field': 'name',
        'queryset_order': 'name',
        'build_payload': _build_strain_payload,
        'output_key': 'text_content',
        'target_field': 'text_content',
        'translate_model_name': 'Strain',
        'translate_field': 'text_content',
    },
    'terpene': {
        'label': 'Terpene',
        'name_field': 'name',
        'queryset_order': 'name',
        'build_payload': _build_terpene_payload,
        'output_key': 'description',
        'target_field': 'description',
        'translate_model_name': 'Terpene',
        'translate_field': 'description',
    },
    'article': {
        'label': 'Article',
        'name_field': 'title_en',
        'queryset_order': 'title_en',
        'build_payload': _build_article_payload,
        'output_key': 'text_content',
        'target_field': 'text_content',
        'translate_model_name': 'Article',
        'translate_field': 'text_content',
    },
}


def get_handler(content_type: str) -> dict:
    """Return handler dict with lazily resolved _model_class."""
    handler = CONTENT_TYPE_HANDLERS.get(content_type)
    if not handler:
        raise ValueError(f'Unknown content type: {content_type}')
    if '_model_class' not in handler:
        handler['_model_class'] = _get_model_class(content_type)
    return handler


# ---------------------------------------------------------------------------
# Generic copywriter
# ---------------------------------------------------------------------------

class CopywritingError(Exception):
    pass


class GenericCopywriter:
    """LLM copywriter using static config from copywriter_config."""

    def __init__(self, config: dict):
        self.system_prompt = config['system_prompt']
        self.model = config['model']
        self.temperature = config['temperature']
        self.max_tokens = config['max_tokens']
        self._init_client()

    def _init_client(self):
        from openai import OpenAI
        self.client = OpenAI(
            api_key=TranslationConfig.OPENAI_API_KEY,
            timeout=TranslationConfig.OPENAI_TIMEOUT,
        )

    def generate(self, source_text: str, obj=None, content_type: str = '') -> dict:
        handler = get_handler(content_type)
        user_payload = handler['build_payload'](source_text, obj)
        result = self._generate_json(user_payload)

        output_key = handler['output_key']
        text = result.get(output_key, '')
        if not str(text).strip():
            raise CopywritingError(f'LLM returned empty {output_key}')

        result[output_key] = clean_generated_output(str(text).strip(), content_type)
        return result

    def _generate_json(self, user_payload: str) -> dict:
        raw = self._call_model(user_payload)
        raw = strip_code_fences(raw)
        try:
            return json.loads(raw)
        except json.JSONDecodeError as exc:
            raise CopywritingError(f'Invalid JSON from LLM: {exc}') from exc

    def _call_model(self, user_payload: str) -> str:
        from openai import OpenAIError
        try:
            response = create_chat_completion(
                self.client,
                model=self.model,
                messages=[
                    {'role': 'system', 'content': self.system_prompt},
                    {'role': 'user', 'content': user_payload},
                ],
                temperature=self.temperature,
                max_tokens=self.max_tokens,
            )
        except OpenAIError as exc:
            raise CopywritingError(str(exc)) from exc
        return response.choices[0].message.content.strip()


def get_copywriter_for_content_type(content_type: str) -> GenericCopywriter:
    """Factory: return a copywriter configured from static config."""
    config = get_config(content_type)
    return GenericCopywriter(config)
