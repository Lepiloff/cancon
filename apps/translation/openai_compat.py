from __future__ import annotations

from typing import Any

from openai import OpenAIError


def _prefers_max_completion_tokens(model: str) -> bool:
    normalized = (model or '').strip().lower()
    return normalized.startswith(('gpt-5', 'o1', 'o3', 'o4'))


def _supports_retry(error: OpenAIError, unsupported_param: str, replacement_param: str) -> bool:
    message = str(error)
    return (
        f"Unsupported parameter: '{unsupported_param}'" in message
        and replacement_param in message
    )


def create_chat_completion(
    client: Any,
    *,
    model: str,
    messages: list[dict[str, str]],
    temperature: float | None = None,
    max_tokens: int | None = None,
    **extra_kwargs: Any,
) -> Any:
    request_kwargs: dict[str, Any] = {
        'model': model,
        'messages': messages,
        **extra_kwargs,
    }
    if temperature is not None:
        request_kwargs['temperature'] = temperature

    token_param: str | None = None
    if max_tokens is not None:
        token_param = 'max_completion_tokens' if _prefers_max_completion_tokens(model) else 'max_tokens'
        request_kwargs[token_param] = max_tokens

    try:
        return client.chat.completions.create(**request_kwargs)
    except OpenAIError as exc:
        if (
            token_param == 'max_tokens'
            and max_tokens is not None
            and _supports_retry(exc, 'max_tokens', 'max_completion_tokens')
        ):
            request_kwargs.pop('max_tokens', None)
            request_kwargs['max_completion_tokens'] = max_tokens
            return client.chat.completions.create(**request_kwargs)
        if (
            token_param == 'max_completion_tokens'
            and max_tokens is not None
            and _supports_retry(exc, 'max_completion_tokens', 'max_tokens')
        ):
            request_kwargs.pop('max_completion_tokens', None)
            request_kwargs['max_tokens'] = max_tokens
            return client.chat.completions.create(**request_kwargs)
        raise
