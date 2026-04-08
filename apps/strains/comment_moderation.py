import json
import logging
import re
from dataclasses import dataclass

from openai import OpenAI
from openai import OpenAIError

from apps.translation.config import TranslationConfig
from apps.translation.openai_compat import create_chat_completion


logger = logging.getLogger(__name__)

PROFANITY_PATTERNS = [
    r'\bfuck(?:ing|ed|er)?\b',
    r'\bshit(?:ty)?\b',
    r'\basshole\b',
    r'\bbitch(?:es)?\b',
    r'\bputa\b',
    r'\bmierda\b',
    r'\bjoder\b',
    r'\bcabron(?:es)?\b',
    r'\bco(?:n|ñ)o\b',
    r'\bcarajo\b',
]


@dataclass
class ModerationResult:
    status: str
    reason: str = ''


def moderate_strain_comment(pros: str, cons: str) -> ModerationResult:
    text = ' '.join(part.strip() for part in [pros, cons] if part and part.strip())

    if _matches_local_profanity(text):
        return ModerationResult(status='rejected', reason='local_profanity_match')

    if not text:
        return ModerationResult(status='pending', reason='empty_comment')

    if not TranslationConfig.OPENAI_API_KEY:
        return ModerationResult(status='approved', reason='heuristic_only')

    try:
        return _moderate_with_openai(text)
    except OpenAIError as exc:
        logger.warning('Comment moderation provider error: %s', exc)
        return ModerationResult(status='pending', reason='provider_error')
    except (json.JSONDecodeError, KeyError, ValueError) as exc:
        logger.warning('Comment moderation parse error: %s', exc)
        return ModerationResult(status='pending', reason='provider_parse_error')


def _matches_local_profanity(text: str) -> bool:
    normalized = (text or '').lower()
    return any(re.search(pattern, normalized, re.IGNORECASE) for pattern in PROFANITY_PATTERNS)


def _moderate_with_openai(text: str) -> ModerationResult:
    client = OpenAI(
        api_key=TranslationConfig.OPENAI_API_KEY,
        timeout=TranslationConfig.OPENAI_TIMEOUT,
    )
    response = create_chat_completion(
        client,
        model=TranslationConfig.OPENAI_MODEL,
        temperature=0,
        max_tokens=120,
        messages=[
            {
                'role': 'system',
                'content': (
                    'You moderate short public cannabis strain comments. '
                    'Reject profanity, hate, threats, sexual explicitness, or spam. '
                    'Approve normal subjective opinions. '
                    'Return strict JSON: {"status":"approved|rejected","reason":"short_reason"}.'
                ),
            },
            {'role': 'user', 'content': text},
        ],
    )

    content = (response.choices[0].message.content or '').strip()
    if content.startswith('```'):
        lines = content.split('\n')
        lines = lines[1:]
        if lines and lines[-1].strip() == '```':
            lines = lines[:-1]
        content = '\n'.join(lines).strip()

    payload = json.loads(content)
    status = payload['status']
    if status not in {'approved', 'rejected'}:
        raise ValueError(f'Unsupported moderation status: {status}')

    return ModerationResult(status=status, reason=payload.get('reason', ''))
