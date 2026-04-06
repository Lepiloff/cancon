from __future__ import annotations

import logging
import re

from bs4 import BeautifulSoup, Comment

logger = logging.getLogger(__name__)

AI_WORDS = {
    'landscape', 'interplay', 'testament', 'tapestry', 'multifaceted',
    'pivotal', 'cornerstone', 'renowned', 'paradigm', 'leverage',
    'comprehensive', 'robust', 'nuanced', 'intricate', 'innovative',
    'holistic', 'synergy', 'delve', 'elevate', 'captivating', 'embark',
    'foster', 'moreover', 'furthermore', 'notably',
}


def strip_code_fences(content: str) -> str:
    if content.startswith('```'):
        lines = content.split('\n')
        lines = lines[1:]
        if lines and lines[-1].strip() == '```':
            lines = lines[:-1]
        return '\n'.join(lines).strip()
    return content


def normalize_ascii_punctuation(text: str) -> str:
    replacements = {
        '\u2018': "'",
        '\u2019': "'",
        '\u201c': '"',
        '\u201d': '"',
        '\u2013': '-',
        '\u2014': '-',
        '\u2026': '...',
        '\u00a0': ' ',
    }
    for original, replacement in replacements.items():
        text = text.replace(original, replacement)
    return text


def _check_ai_words(text: str) -> list[str]:
    lower = text.lower()
    return [word for word in AI_WORDS if re.search(rf'\b{word}\b', lower)]


def humanize_text(text: str) -> str:
    text = normalize_ascii_punctuation(text)
    found = _check_ai_words(text)
    if found:
        logger.warning('AI words detected in copywriter output: %s', ', '.join(found))
    return text


def strip_links(text: str) -> str:
    soup = BeautifulSoup(text, 'html.parser')
    for anchor in soup.find_all('a'):
        anchor.replace_with(anchor.get_text(' ', strip=True))
    return _render_html(soup)


def ensure_paragraph(text: str) -> str:
    stripped = text.strip()
    if stripped.lower().startswith('<p>') and stripped.lower().endswith('</p>'):
        return stripped
    return f'<p>{stripped}</p>'


def sanitize_html(
    text: str,
    *,
    allowed_tags: set[str],
    allowed_attrs: dict[str, set[str]] | None = None,
) -> str:
    soup = BeautifulSoup(text, 'html.parser')

    for comment in soup.find_all(string=lambda value: isinstance(value, Comment)):
        comment.extract()

    for tag in soup.find_all(True):
        tag_name = tag.name.lower()
        if tag_name in {'script', 'style'}:
            tag.decompose()
            continue
        if tag_name not in allowed_tags:
            tag.unwrap()
            continue

        allowed_for_tag = (allowed_attrs or {}).get(tag_name, set())
        for attr_name in list(tag.attrs):
            if attr_name not in allowed_for_tag:
                del tag.attrs[attr_name]

    return _render_html(soup)


def clean_generated_output(text: str, content_type: str) -> str:
    cleaned = humanize_text(str(text or '').strip())

    if content_type == 'terpene':
        cleaned = strip_links(cleaned)
        cleaned = BeautifulSoup(cleaned, 'html.parser').get_text('\n')
        return _normalize_plain_text_blocks(cleaned)

    cleaned = strip_links(cleaned)

    if content_type == 'strain':
        cleaned = sanitize_html(cleaned, allowed_tags={'p'})
        return ensure_paragraph(cleaned)

    if content_type == 'article':
        cleaned = sanitize_html(
            cleaned,
            allowed_tags={'p', 'h3', 'ul', 'li', 'strong', 'em'},
        )
        return cleaned.strip()

    raise ValueError(f'Unknown content type: {content_type}')


def _render_html(soup: BeautifulSoup) -> str:
    container = soup.body if soup.body else soup
    return ''.join(str(child) for child in container.contents).strip()


def _normalize_plain_text_blocks(text: str) -> str:
    text = text.replace('\r\n', '\n').replace('\r', '\n')
    normalized_lines: list[str] = []

    for raw_line in text.split('\n'):
        line = re.sub(r'\s+', ' ', raw_line).strip()
        if not line:
            if normalized_lines and normalized_lines[-1] != '':
                normalized_lines.append('')
            continue
        normalized_lines.append(line)

    while normalized_lines and normalized_lines[-1] == '':
        normalized_lines.pop()

    return '\n'.join(normalized_lines)
