#!/usr/bin/env python3
"""
Compare text generation quality: OpenAI vs Claude.

Usage:
    python scripts/compare_llm_quality.py
    python scripts/compare_llm_quality.py --strains gorilla-glue blue-dream og-kush
    python scripts/compare_llm_quality.py --provider openai   # only one provider
"""

import argparse
import os
import re
import sys
import textwrap
import time
from pathlib import Path

# Django setup
BASE_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BASE_DIR))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'canna.settings')

# Load .env manually (no python-dotenv dependency needed)
_env_file = BASE_DIR / '.env'
if _env_file.exists():
    with open(_env_file) as _f:
        for _line in _f:
            _line = _line.strip()
            if _line and not _line.startswith('#') and '=' in _line:
                _key, _, _val = _line.partition('=')
                os.environ.setdefault(_key.strip(), _val.strip())

import django  # noqa: E402
django.setup()

from apps.strains.leafly_import import (  # noqa: E402
    LeaflyClient,
    LeaflyParser,
    LeaflyCopywriter,
    ClaudeCopywriter,
    CopywritingError,
)
from apps.translation.config import TranslationConfig  # noqa: E402


# ─── Test strains ──────────────────────────────────────────────────────────────
DEFAULT_STRAINS = ['blue-dream', 'runtz', 'og-kush']

WIDTH = 80  # console column width for text wrapping


# ─── Metrics ───────────────────────────────────────────────────────────────────

def strip_html(text: str) -> str:
    return re.sub(r'<[^>]+>', '', text)


def count_em_dashes(text: str) -> int:
    return text.count('\u2014') + text.count(' - ')


def metrics(raw_text: str) -> dict:
    clean = strip_html(raw_text)
    sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', clean) if s.strip()]
    words = clean.split()
    return {
        'words': len(words),
        'chars': len(clean),
        'sentences': len(sentences),
        'em_dashes': count_em_dashes(raw_text),
        'avg_sentence_len': round(len(words) / max(len(sentences), 1), 1),
    }


def print_separator(char='═', width=WIDTH * 2 + 7):
    print(char * width)


def print_header(title: str):
    print_separator('═')
    print(f'  {title}')
    print_separator('═')


def print_comparison(strain_name: str, results: dict):
    """Print two descriptions side by side with metrics."""
    print_separator('─')
    print(f'  STRAIN: {strain_name.upper()}')
    print_separator('─')

    providers = list(results.keys())

    # Header row
    col = WIDTH
    header = '  ' + ''.join(f'{p.upper():<{col}}  ' for p in providers)
    print(header)
    print()

    # Wrap text into lines
    wrapped = {}
    for p in providers:
        text = strip_html(results[p]['text'])
        wrapped[p] = textwrap.wrap(text, width=col) if text else ['[FAILED]']

    max_lines = max(len(wrapped[p]) for p in providers)
    for i in range(max_lines):
        row = '  '
        for p in providers:
            lines = wrapped[p]
            cell = lines[i] if i < len(lines) else ''
            row += f'{cell:<{col}}  '
        print(row)

    print()

    # Metrics row
    for p in providers:
        m = results[p].get('metrics')
        if not m:
            continue
        em = f' ⚠️  em-dashes: {m["em_dashes"]}' if m['em_dashes'] else ''
        print(
            f'  [{p.upper()}] '
            f'words={m["words"]}  '
            f'sentences={m["sentences"]}  '
            f'avg_len={m["avg_sentence_len"]} words/sent  '
            f'chars={m["chars"]}'
            f'{em}'
        )
    print()

    # Alt names & img_alt
    for p in providers:
        r = results[p]
        alts = r.get('alternative_names', [])
        img  = r.get('img_alt_text', '')
        if alts or img:
            print(f'  [{p.upper()}] alt_names={alts}  img_alt="{img}"')
    print()


# ─── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description='Compare OpenAI vs Claude copywriting quality')
    parser.add_argument(
        '--strains', nargs='+', default=DEFAULT_STRAINS,
        help='Leafly strain slugs to test',
    )
    parser.add_argument(
        '--provider', choices=['openai', 'anthropic', 'both'], default='both',
        help='Which provider to test (default: both)',
    )
    args = parser.parse_args()

    # ── Init copywriters ──
    copywriters = {}

    if args.provider in ('openai', 'both'):
        openai_key = TranslationConfig.OPENAI_API_KEY
        if openai_key:
            try:
                copywriters['openai'] = LeaflyCopywriter()
                print(f'✓ OpenAI ready  (model={TranslationConfig.OPENAI_MODEL})')
            except Exception as e:
                print(f'✗ OpenAI init failed: {e}')
        else:
            print('✗ OpenAI: OPENAI_API_KEY not set in .env')

    if args.provider in ('anthropic', 'both'):
        anthropic_key = TranslationConfig.ANTHROPIC_API_KEY
        if anthropic_key:
            try:
                copywriters['anthropic'] = ClaudeCopywriter()
                print(f'✓ Claude ready  (model={TranslationConfig.ANTHROPIC_MODEL})')
            except Exception as e:
                print(f'✗ Claude init failed: {e}')
        else:
            print('✗ Claude: ANTHROPIC_API_KEY not set in .env — add it and rerun')

    if not copywriters:
        print('\nNo LLM providers available. Check .env')
        sys.exit(1)

    print()

    # ── Fetch & generate ──
    client = LeaflyClient()
    parser_lf = LeaflyParser()

    all_results = {}

    for slug in args.strains:
        print(f'Fetching Leafly: {slug}...')
        try:
            html = client.fetch(slug)
            parsed = parser_lf.parse(html)
        except Exception as e:
            print(f'  ✗ Failed to fetch/parse {slug}: {e}\n')
            continue

        print(f'  → {parsed.name} | {parsed.category} | THC={parsed.thc}% | {len(parsed.description_text)} chars source')

        strain_results = {}
        for provider, cw in copywriters.items():
            print(f'  Generating with {provider}...')
            try:
                t0 = time.time()
                output = cw.rewrite(parsed)
                elapsed = time.time() - t0
                text = output['text_content']
                m = metrics(text)
                strain_results[provider] = {
                    'text': text,
                    'img_alt_text': output.get('img_alt_text', ''),
                    'alternative_names': output.get('alternative_names', []),
                    'metrics': m,
                    'elapsed': round(elapsed, 2),
                }
                em_warn = f' ⚠️  {m["em_dashes"]} em-dashes' if m['em_dashes'] else ''
                print(f'  ✓ {provider}: {m["words"]} words, {m["sentences"]} sentences, {elapsed:.1f}s{em_warn}')
            except CopywritingError as e:
                print(f'  ✗ {provider} failed: {e}')
                strain_results[provider] = {'text': f'[ERROR: {e}]', 'metrics': None}

        all_results[slug] = (parsed.name, strain_results)
        print()
        time.sleep(1)  # small pause between strains

    # ── Print full comparison ──
    print_header('FULL TEXT COMPARISON')
    for slug, (name, results) in all_results.items():
        print_comparison(name, results)

    # ── Summary ──
    print_separator('═')
    print('  SUMMARY')
    print_separator('─')
    for slug, (name, results) in all_results.items():
        print(f'  {name}:')
        for provider, r in results.items():
            m = r.get('metrics')
            if m:
                em = f' | ⚠️  {m["em_dashes"]} em-dashes' if m['em_dashes'] else ''
                print(f'    {provider:12s}: {m["words"]:3d} words, {m["sentences"]} sent, avg {m["avg_sentence_len"]} w/s{em}')
    print_separator('═')


if __name__ == '__main__':
    main()
