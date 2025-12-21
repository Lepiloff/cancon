import json
import random
import re
import time
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

import requests
from bs4 import BeautifulSoup
from openai import OpenAI, OpenAIError

from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from apps.strains.models import (
    AlternativeStrainName,
    Feeling,
    Flavor,
    HelpsWith,
    Negative,
    Strain,
    Terpene,
)
from apps.translation import OpenAITranslator, TranslationConfig
from apps.translation.base_translator import TranslationError


def _strip_code_fences(content: str) -> str:
    if content.startswith('```'):
        lines = content.split('\n')
        lines = lines[1:]
        if lines and lines[-1].strip() == '```':
            lines = lines[:-1]
        return '\n'.join(lines).strip()
    return content


class LeaflyFetchError(Exception):
    pass


class LeaflyParseError(Exception):
    pass


class CopywritingError(Exception):
    pass


class TaxonomyTranslationError(Exception):
    pass


@dataclass
class ParsedLeaflyStrain:
    name: str
    category: str
    rating: Optional[Decimal]
    thc: Optional[Decimal]
    cbd: Optional[Decimal]
    cbg: Optional[Decimal]
    description_text: str
    feelings: List[str]
    negatives: List[str]
    helps_with: List[str]
    flavors: List[str]
    terpenes: List[str]


class LeaflyClient:
    def __init__(self, timeout: int = 15, retries: int = 2):
        self.timeout = timeout
        self.retries = retries
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': (
                'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 '
                '(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'
            ),
            'Accept-Language': 'en-US,en;q=0.9',
        })

    def fetch(self, alias: str) -> str:
        url = f'https://www.leafly.com/strains/{alias}'
        last_error = None
        for attempt in range(self.retries + 1):
            try:
                response = self.session.get(url, timeout=self.timeout)
                if response.status_code == 200:
                    return response.text
                if response.status_code == 404:
                    raise LeaflyFetchError(f'Leafly page not found: {url}')
                if response.status_code in (429, 500, 502, 503, 504):
                    last_error = LeaflyFetchError(
                        f'Leafly response {response.status_code} for {url}'
                    )
                    time.sleep(2 ** attempt)
                    continue
                raise LeaflyFetchError(
                    f'Leafly response {response.status_code} for {url}'
                )
            except requests.RequestException as exc:
                last_error = LeaflyFetchError(str(exc))
                time.sleep(2 ** attempt)
        raise last_error or LeaflyFetchError(f'Failed to fetch {url}')


class LeaflyParser:
    CATEGORY_MAP = {
        'hybrid': 'Hybrid',
        'indica': 'Indica',
        'sativa': 'Sativa',
    }
    LOADING_PATTERN = re.compile(r'(loading\.\.\.|cargando\.\.\.)', re.I)
    EFFECTS_LIMIT = 3
    NEGATIVES_LIMIT = 3
    FLAVORS_LIMIT = 3
    HELPS_WITH_LIMIT = 4
    TERPENES_LIMIT = 3

    def parse(self, html: str) -> ParsedLeaflyStrain:
        next_data = self._parse_next_data(html)
        if next_data:
            parsed = self._parse_from_next_data(next_data)
            if parsed:
                return parsed

        soup = BeautifulSoup(html, 'html.parser')
        name = self._parse_name(soup)
        if not name:
            raise LeaflyParseError('Unable to parse strain name')

        category = self._parse_category(soup)
        if not category:
            raise LeaflyParseError('Unable to parse strain category')

        description_text = self._parse_description_text(soup, name)
        if not description_text:
            raise LeaflyParseError('Unable to parse description text')

        rating = self._parse_rating(soup)
        thc = self._parse_percentage(soup, 'THC')
        cbd = self._parse_percentage(soup, 'CBD')
        cbg = self._parse_percentage(soup, 'CBG')

        feelings = self._select_terms(
            primary=self._parse_section_terms(soup, heading_texts=('Effects', 'Feelings')),
            fallback=self._parse_anchor_terms(
                soup,
                patterns=('/strains/lists/effect/', 'effects_included='),
            ),
        )
        negatives = self._select_terms(
            primary=self._parse_section_terms(soup, heading_texts=('Negatives', 'Negative effects')),
            fallback=self._parse_anchor_terms(
                soup,
                patterns=('/strains/lists/negative/', 'negatives_included=', 'negative_effects_included='),
            ),
        )
        helps_with = self._select_terms(
            primary=self._parse_section_terms(soup, heading_texts=('Helps with', 'Helps With')),
            fallback=self._parse_anchor_terms(
                soup,
                patterns=('/strains/lists/condition/', 'conditions_included=', 'symptoms_included='),
            ),
        )
        flavors = self._select_terms(
            primary=self._parse_section_terms(soup, heading_texts=('Flavors', 'Flavour', 'Flavours')),
            fallback=self._parse_anchor_terms(
                soup,
                patterns=('/strains/lists/flavor/', 'flavors_included='),
            ),
        )
        terpenes = self._merge_terms(
            primary=self._parse_section_terms(soup, heading_texts=('Terpenes',)),
            secondary=self._parse_anchor_terms(
                soup,
                patterns=('/strains/lists/terpene/', 'strain_top_terp='),
            ),
        )
        feelings = feelings[: self.EFFECTS_LIMIT]
        negatives = negatives[: self.NEGATIVES_LIMIT]
        flavors = flavors[: self.FLAVORS_LIMIT]
        helps_with = helps_with[: self.HELPS_WITH_LIMIT]
        terpenes = terpenes[: self.TERPENES_LIMIT]

        return ParsedLeaflyStrain(
            name=name,
            category=category,
            rating=rating,
            thc=thc,
            cbd=cbd,
            cbg=cbg,
            description_text=description_text,
            feelings=feelings,
            negatives=negatives,
            helps_with=helps_with,
            flavors=flavors,
            terpenes=terpenes,
        )

    def _parse_name(self, soup: BeautifulSoup) -> Optional[str]:
        heading = soup.find('h1')
        if heading:
            name = heading.get_text(strip=True)
            if name:
                return name
        og_title = soup.find('meta', attrs={'property': 'og:title'})
        if og_title and og_title.get('content'):
            return og_title['content'].split('|')[0].strip()
        return None

    def _parse_category(self, soup: BeautifulSoup) -> Optional[str]:
        category_link = soup.find('a', href=re.compile(r'/strains/lists/category/'))
        if category_link:
            category_text = category_link.get_text(strip=True)
            if category_text:
                return self.CATEGORY_MAP.get(category_text.lower())
        for value in self.CATEGORY_MAP.values():
            tag = soup.find(string=re.compile(rf'^{re.escape(value)}$', re.I))
            if tag:
                return value
        return None

    def _parse_description_text(self, soup: BeautifulSoup, name: str) -> str:
        selectors = [
            '[data-testid="strain-description"] p',
            '[data-testid="strain-description-text"] p',
        ]
        for selector in selectors:
            node = soup.select_one(selector)
            if node:
                text = node.get_text(' ', strip=True)
                if text:
                    return text

        longest_text = ''
        longest_name_text = ''
        name_lower = name.lower()
        for paragraph in soup.find_all('p'):
            text = paragraph.get_text(' ', strip=True)
            if len(text) > len(longest_text):
                longest_text = text
            if name_lower and name_lower in text.lower() and len(text) > len(longest_name_text):
                longest_name_text = text
        if longest_name_text:
            return longest_name_text.strip()
        return longest_text.strip()

    def _parse_next_data(self, html: str) -> Optional[dict]:
        match = re.search(
            r'__NEXT_DATA__\" type=\"application/json\">(.*?)</script>',
            html,
            re.S,
        )
        if not match:
            return None
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            return None

    def _parse_from_next_data(self, data: dict) -> Optional[ParsedLeaflyStrain]:
        strain = (
            data.get('props', {})
            .get('pageProps', {})
            .get('strain')
        )
        if not isinstance(strain, dict):
            return None

        name = strain.get('name')
        category = strain.get('category')
        if not name or not category:
            return None

        category = self.CATEGORY_MAP.get(str(category).lower(), category)
        rating = self._parse_decimal_from_text(strain.get('rating'), Decimal('0.1'))

        description_text = (
            strain.get('descriptionPlain')
            or self._strip_html(strain.get('description', ''))
        )
        description_text = str(description_text).strip()

        cannabinoids = strain.get('cannabinoids', {}) or {}
        thc = self._parse_decimal_from_text(
            (cannabinoids.get('thc') or {}).get('percentile50'),
            Decimal('0.01'),
        )
        cbd = self._parse_decimal_from_text(
            (cannabinoids.get('cbd') or {}).get('percentile50'),
            Decimal('0.01'),
        )
        cbg = self._parse_decimal_from_text(
            (cannabinoids.get('cbg') or {}).get('percentile50'),
            Decimal('0.01'),
        )

        effects = self._extract_ranked_terms(
            strain.get('effects', {}),
            limit=self.EFFECTS_LIMIT,
        )
        negatives = self._extract_ranked_terms(
            strain.get('negatives', {}),
            limit=self.NEGATIVES_LIMIT,
        )
        flavors = self._extract_ranked_terms(
            strain.get('flavors', {}),
            limit=self.FLAVORS_LIMIT,
        )
        helps_with_source = self._merge_trait_dicts(
            strain.get('conditions', {}),
            strain.get('symptoms', {}),
        )
        helps_with = self._extract_ranked_terms(
            helps_with_source,
            limit=self.HELPS_WITH_LIMIT,
        )
        terpenes = self._extract_ranked_terms(
            strain.get('terps', {}),
            limit=self.TERPENES_LIMIT,
        )

        return ParsedLeaflyStrain(
            name=str(name).strip(),
            category=category,
            rating=rating,
            thc=thc,
            cbd=cbd,
            cbg=cbg,
            description_text=description_text,
            feelings=effects,
            negatives=negatives,
            helps_with=helps_with,
            flavors=flavors,
            terpenes=terpenes,
        )

    def _merge_trait_dicts(self, *dicts) -> List[dict]:
        merged = {}
        for source in dicts:
            if not isinstance(source, dict):
                continue
            for item in source.values():
                name = item.get('name')
                if not name:
                    continue
                key = name.lower()
                score = item.get('score', 0) or 0
                votes = item.get('votes', 0) or 0
                existing = merged.get(key)
                if not existing or score > existing.get('score', 0):
                    merged[key] = {
                        'name': name,
                        'score': score,
                        'votes': votes,
                    }
        return list(merged.values())

    def _extract_ranked_terms(self, source, limit: int) -> List[str]:
        if not source:
            return []
        if isinstance(source, dict):
            items = list(source.values())
        elif isinstance(source, list):
            items = source
        else:
            return []

        items = [item for item in items if isinstance(item, dict) and item.get('name')]
        items.sort(
            key=lambda item: (item.get('score', 0) or 0, item.get('votes', 0) or 0),
            reverse=True,
        )
        terms = [item['name'] for item in items[:limit]]
        return self._clean_terms(terms)

    def _strip_html(self, text: str) -> str:
        soup = BeautifulSoup(text or '', 'html.parser')
        return soup.get_text(' ', strip=True)

    def _parse_rating(self, soup: BeautifulSoup) -> Optional[Decimal]:
        for script in soup.find_all('script', attrs={'type': 'application/ld+json'}):
            if not script.string:
                continue
            try:
                data = json.loads(script.string)
            except json.JSONDecodeError:
                continue
            rating = self._extract_rating_from_json(data)
            if rating is not None:
                return rating

        rating_tag = soup.find(attrs={'data-testid': re.compile('rating', re.I)})
        if rating_tag:
                return self._parse_decimal_from_text(
                    rating_tag.get_text(' ', strip=True),
                    quantize=Decimal('0.1'),
                )
        return None

    def _extract_rating_from_json(self, data) -> Optional[Decimal]:
        if isinstance(data, list):
            for item in data:
                rating = self._extract_rating_from_json(item)
                if rating is not None:
                    return rating
        if isinstance(data, dict):
            aggregate = data.get('aggregateRating') or {}
            if isinstance(aggregate, dict) and aggregate.get('ratingValue'):
                return self._parse_decimal_from_text(
                    str(aggregate.get('ratingValue')),
                    quantize=Decimal('0.1'),
                )
            for value in data.values():
                rating = self._extract_rating_from_json(value)
                if rating is not None:
                    return rating
        return None

    def _parse_percentage(self, soup: BeautifulSoup, label: str) -> Optional[Decimal]:
        node = soup.find(attrs={'data-testid': label})
        if not node:
            return None
        text = node.get_text(' ', strip=True)
        match = re.search(r'([0-9]+(?:\.[0-9]+)?)\s*%', text)
        if not match:
            return None
        return self._parse_decimal_from_text(match.group(1), quantize=Decimal('0.01'))

    def _parse_anchor_terms(self, soup: BeautifulSoup, patterns: Sequence[str]) -> List[str]:
        results = []
        seen = set()
        for anchor in soup.find_all('a', href=True):
            href = anchor['href']
            if not any(pattern in href for pattern in patterns):
                continue
            text = anchor.get_text(' ', strip=True)
            if not text:
                continue
            key = text.lower()
            if key not in seen:
                seen.add(key)
                results.append(text)
        return results

    def _parse_section_terms(
        self,
        soup: BeautifulSoup,
        heading_texts: Sequence[str],
    ) -> List[str]:
        for heading_text in heading_texts:
            heading = soup.find(string=re.compile(rf'^{re.escape(heading_text)}$', re.I))
            if not heading:
                continue
            section = heading.find_parent()
            for _ in range(3):
                if section and section.find_all(class_=re.compile('inline-flex')):
                    break
                section = section.parent if section else None
            if not section:
                continue

            terms = []
            seen = set()
            for item in section.find_all(class_=re.compile('inline-flex')):
                text = item.get_text(' ', strip=True)
                if not text or text.lower() == heading_text.lower():
                    continue
                key = text.lower()
                if key not in seen:
                    seen.add(key)
                    terms.append(text)
            if terms:
                return terms
        return []

    def _select_terms(self, primary: List[str], fallback: List[str]) -> List[str]:
        return self._clean_terms(primary if primary else fallback)

    def _merge_terms(self, primary: List[str], secondary: List[str]) -> List[str]:
        return self._clean_terms(primary + secondary)

    def _clean_terms(self, terms: Sequence[str]) -> List[str]:
        cleaned = []
        seen = set()
        for term in terms:
            if not term:
                continue
            text = term.strip()
            text = self.LOADING_PATTERN.sub('', text).strip()
            text = re.sub(r'\s+', ' ', text).strip()
            if not text:
                continue
            key = text.lower()
            if key in seen:
                continue
            seen.add(key)
            cleaned.append(text)
        return cleaned

    def _parse_decimal_from_text(
        self,
        value: str,
        quantize: Decimal,
    ) -> Optional[Decimal]:
        match = re.search(r'([0-9]+(?:\.[0-9]+)?)', str(value))
        if not match:
            return None
        try:
            return Decimal(match.group(1)).quantize(quantize)
        except (InvalidOperation, ValueError):
            return None


class LeaflyCopywriter:
    def __init__(self):
        TranslationConfig.validate()
        self.client = OpenAI(
            api_key=TranslationConfig.OPENAI_API_KEY,
            timeout=TranslationConfig.OPENAI_TIMEOUT,
        )
        self.model = TranslationConfig.OPENAI_MODEL
        self.temperature = TranslationConfig.OPENAI_TEMPERATURE
        self.max_tokens = TranslationConfig.OPENAI_MAX_TOKENS

    def rewrite(self, parsed: ParsedLeaflyStrain) -> Dict[str, object]:
        payload = {
            'strain_name': parsed.name,
            'category': parsed.category,
            'rating': str(parsed.rating) if parsed.rating is not None else None,
            'thc': str(parsed.thc) if parsed.thc is not None else None,
            'cbd': str(parsed.cbd) if parsed.cbd is not None else None,
            'cbg': str(parsed.cbg) if parsed.cbg is not None else None,
            'feelings': parsed.feelings,
            'negatives': parsed.negatives,
            'helps_with': parsed.helps_with,
            'flavors': parsed.flavors,
            'terpenes': parsed.terpenes,
            'description_source': parsed.description_text,
            'target_length': len(parsed.description_text),
        }

        system_prompt = (
            "You are a cannabis SEO copywriter. Rewrite the source description into a "
            "unique, SEO-optimized English paragraph.\n\n"
            "Rules:\n"
            "1. Use only the provided facts and names. Do not invent details.\n"
            "2. Preserve genetics references and all strain names exactly as written.\n"
            "3. Output a single <p>...</p> block with length close to target_length.\n"
            "4. Do NOT include links, URLs, or mention Leafly.\n"
            "5. Use only ASCII punctuation. Avoid curly quotes and dashes.\n"
            "6. Identify alternative names only when explicitly stated as 'also known as' or 'aka'.\n\n"
            "Return ONLY a JSON object with keys:\n"
            "- text_content (string)\n"
            "- img_alt_text (string)\n"
            "- alternative_names (array of strings)\n"
        )

        user_prompt = json.dumps(payload, ensure_ascii=False, indent=2)

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=self.temperature,
                max_tokens=self.max_tokens,
            )
        except OpenAIError as exc:
            raise CopywritingError(str(exc)) from exc

        content = response.choices[0].message.content.strip()
        content = _strip_code_fences(content)

        try:
            result = json.loads(content)
        except json.JSONDecodeError as exc:
            raise CopywritingError(f'Invalid JSON from copywriter: {exc}') from exc

        text_content = str(result.get('text_content', '')).strip()
        text_content = self._normalize_ascii_punctuation(text_content)
        text_content = self._strip_links(text_content)
        text_content = self._ensure_paragraph(text_content)

        img_alt_text = str(result.get('img_alt_text', '')).strip()
        img_alt_text = self._normalize_ascii_punctuation(img_alt_text)

        alternative_names = result.get('alternative_names') or []
        if not isinstance(alternative_names, list):
            alternative_names = []
        alternative_names = self._clean_alternative_names(
            parsed.name,
            [str(name).strip() for name in alternative_names if str(name).strip()],
        )

        if not text_content:
            raise CopywritingError('Copywriter returned empty text_content')
        if not img_alt_text:
            img_alt_text = f'{parsed.name} weed strain image'

        return {
            'text_content': text_content,
            'img_alt_text': img_alt_text,
            'alternative_names': alternative_names,
        }

    def _ensure_paragraph(self, text: str) -> str:
        stripped = text.strip()
        if stripped.lower().startswith('<p>') and stripped.lower().endswith('</p>'):
            return stripped
        return f'<p>{stripped}</p>'

    def _strip_links(self, text: str) -> str:
        soup = BeautifulSoup(text, 'html.parser')
        for anchor in soup.find_all('a'):
            anchor.replace_with(anchor.get_text(' ', strip=True))
        return str(soup)

    def _normalize_ascii_punctuation(self, text: str) -> str:
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

    def _clean_alternative_names(self, primary: str, names: List[str]) -> List[str]:
        cleaned = []
        seen = set()
        primary_lower = primary.strip().lower()
        for name in names:
            if not name:
                continue
            lower = name.lower()
            if lower == primary_lower:
                continue
            if lower in seen:
                continue
            seen.add(lower)
            cleaned.append(name)
        return cleaned


class TaxonomyTranslator:
    def __init__(self):
        TranslationConfig.validate()
        self.client = OpenAI(
            api_key=TranslationConfig.OPENAI_API_KEY,
            timeout=TranslationConfig.OPENAI_TIMEOUT,
        )
        self.model = TranslationConfig.OPENAI_MODEL
        self.temperature = 0.2
        self.max_tokens = 500

    def translate_terms(self, terms: Sequence[str]) -> Dict[str, str]:
        terms = [term for term in terms if term]
        if not terms:
            return {}

        system_prompt = (
            "Translate cannabis taxonomy terms from English to Spanish.\n"
            "Rules:\n"
            "1. Keep acronyms unchanged (e.g., PTSD, ADD/ADHD).\n"
            "2. Return JSON mapping each input term to its Spanish translation.\n"
            "3. Use only ASCII punctuation.\n"
            "4. Do not add extra keys.\n"
        )
        user_prompt = json.dumps({'terms': terms}, ensure_ascii=False, indent=2)

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=self.temperature,
                max_tokens=self.max_tokens,
            )
        except OpenAIError as exc:
            raise TaxonomyTranslationError(str(exc)) from exc

        content = response.choices[0].message.content.strip()
        content = _strip_code_fences(content)

        try:
            mapping = json.loads(content)
        except json.JSONDecodeError as exc:
            raise TaxonomyTranslationError(f'Invalid JSON from taxonomy translator: {exc}') from exc

        if not isinstance(mapping, dict):
            raise TaxonomyTranslationError('Taxonomy translator returned non-object JSON')

        output = {}
        for term in terms:
            translated = mapping.get(term)
            if isinstance(translated, str) and translated.strip():
                output[term] = translated.strip()
        return output


class StrainPersister:
    def __init__(self, taxonomy_translator: TaxonomyTranslator, reporter=None):
        self.taxonomy_translator = taxonomy_translator
        self.reporter = reporter
        self.feeling_cache = self._build_cache(Feeling)
        self.negative_cache = self._build_cache(Negative)
        self.helps_with_cache = self._build_cache(HelpsWith)
        self.flavor_cache = self._build_cache(Flavor)
        self.terpene_cache = self._build_cache(Terpene)

    def persist(
        self,
        parsed: ParsedLeaflyStrain,
        copywriting: Dict[str, object],
        translations: Dict[str, str],
    ) -> Strain:
        with transaction.atomic():
            strain = Strain(
                name=parsed.name,
                title=f'{parsed.name} | Weed Strain',
                description=(
                    f'Learn more about the {parsed.name} weed strain, '
                    'its effects and flavors.'
                ),
                keywords=f'{parsed.name}, cannabis, strain, effects, flavors',
                text_content=copywriting['text_content'],
                img_alt_text=copywriting['img_alt_text'],
                category=parsed.category,
                rating=parsed.rating,
                thc=parsed.thc,
                cbd=parsed.cbd,
                cbg=parsed.cbg,
                active=False,
                is_review=False,
            )

            strain.title_en = strain.title
            strain.description_en = strain.description
            strain.keywords_en = strain.keywords
            strain.text_content_en = strain.text_content
            strain.img_alt_text_en = strain.img_alt_text

            strain.title_es = f'{parsed.name} | Variedad de Cannabis'
            strain.description_es = (
                f'Informaci\u00f3n sobre la variedad de cannabis {parsed.name}, '
                'sus efectos y sabores.'
            )
            strain.keywords_es = f'{parsed.name}, cannabis, variedad, efectos, sabores'
            strain.text_content_es = translations.get('text_content', '')
            strain.img_alt_text_es = translations.get('img_alt_text', '')

            strain.translation_status = 'synced'
            strain.translation_source_hash = strain.get_translatable_content_hash()
            strain.last_translated_at = timezone.now()
            strain.translation_error = None

            random_image = self._get_random_image()
            if random_image:
                strain.img = random_image
                if self.reporter:
                    self.reporter.success('image', f'Assigned random image to {strain.name}')
            elif self.reporter:
                self.reporter.warning('image', f'No images available for {strain.name}')

            dominant, others = self._resolve_terpenes(parsed.terpenes)
            strain.dominant_terpene = dominant
            if self.reporter:
                if dominant:
                    self.reporter.success(
                        'terpenes',
                        f'Dominant terpene: {dominant.name}',
                    )
                else:
                    self.reporter.warning('terpenes', f'No dominant terpene for {strain.name}')

            strain.save()
            if self.reporter:
                self.reporter.success('strain', f'Base fields saved for {strain.name}')

            self._assign_m2m(
                strain.feelings,
                parsed.feelings,
                Feeling,
                self.feeling_cache,
                label='feelings',
            )
            self._assign_m2m(
                strain.negatives,
                parsed.negatives,
                Negative,
                self.negative_cache,
                label='negatives',
            )
            self._assign_m2m(
                strain.helps_with,
                parsed.helps_with,
                HelpsWith,
                self.helps_with_cache,
                label='helps_with',
            )
            self._assign_m2m(
                strain.flavors,
                parsed.flavors,
                Flavor,
                self.flavor_cache,
                label='flavors',
            )
            if others:
                strain.other_terpenes.set(others)
                if self.reporter:
                    self.reporter.success(
                        'terpenes',
                        f'Assigned {len(others)} other terpenes to {strain.name}',
                    )
            elif self.reporter:
                self.reporter.warning('terpenes', f'No other terpenes for {strain.name}')

            alt_names = copywriting.get('alternative_names', [])
            self._create_alternative_names(strain, alt_names)

            return strain

    def _build_cache(self, model):
        cache = {}
        for obj in model.objects.all():
            for attr in ('name', 'name_en', 'name_es'):
                if hasattr(obj, attr):
                    value = getattr(obj, attr, None)
                    if value:
                        cache[value.lower()] = obj
        return cache

    def _resolve_terpenes(self, names: Sequence[str]) -> Tuple[Optional[Terpene], List[Terpene]]:
        if not names:
            return None, []
        terpenes = self._resolve_taxonomy(names, Terpene, self.terpene_cache)
        dominant = terpenes[0] if terpenes else None
        others = [terpene for terpene in terpenes[1:] if terpene != dominant]
        return dominant, others

    def _assign_m2m(self, manager, names, model, cache, label: str):
        if not names:
            if self.reporter:
                self.reporter.warning(label, 'No items found')
            return
        objects = self._resolve_taxonomy(names, model, cache)
        if objects:
            manager.set(objects)
            if self.reporter:
                self.reporter.success(label, f'Assigned {len(objects)} items')

    def _resolve_taxonomy(self, names, model, cache):
        resolved = []
        missing = []
        for name in names:
            key = name.lower()
            obj = cache.get(key)
            if obj:
                resolved.append(obj)
            else:
                missing.append(name)

        translations = {}
        if missing and hasattr(model, 'name_es'):
            translations = self.taxonomy_translator.translate_terms(missing)

        for name in missing:
            lookup = Q()
            if hasattr(model, 'name'):
                lookup |= Q(name__iexact=name)
            if hasattr(model, 'name_en'):
                lookup |= Q(name_en__iexact=name)
            if hasattr(model, 'name_es'):
                lookup |= Q(name_es__iexact=name)
            if lookup:
                existing = model.objects.filter(lookup).first()
                if existing:
                    for attr in ('name', 'name_en', 'name_es'):
                        if hasattr(existing, attr):
                            value = getattr(existing, attr, None)
                            if value:
                                cache[value.lower()] = existing
                    resolved.append(existing)
                    continue
            obj = model(name=name)
            if hasattr(obj, 'name_en'):
                obj.name_en = name
            if hasattr(obj, 'name_es'):
                obj.name_es = translations.get(name, name)
            obj.save()
            for attr in ('name', 'name_en', 'name_es'):
                if hasattr(obj, attr):
                    value = getattr(obj, attr, None)
                    if value:
                        cache[value.lower()] = obj
            resolved.append(obj)

        return resolved

    def _create_alternative_names(self, strain: Strain, names: Iterable[str]):
        created = 0
        for name in names:
            if not name:
                continue
            existing = AlternativeStrainName.objects.filter(name__iexact=name).first()
            if existing:
                continue
            AlternativeStrainName.objects.create(name=name, strain=strain)
            created += 1
        if self.reporter:
            if created:
                self.reporter.success('aliases', f'Added {created} alternative names')
            else:
                self.reporter.info('aliases', 'No alternative names added')

    def _get_random_image(self):
        ids = list(
            Strain.objects.exclude(img__isnull=True)
            .exclude(img='')
            .values_list('id', flat=True)
        )
        if not ids:
            return None
        image_strain = Strain.objects.get(id=random.choice(ids))
        return image_strain.img


class LeaflyImporter:
    def __init__(
        self,
        reporter,
        client: Optional[LeaflyClient] = None,
        parser: Optional[LeaflyParser] = None,
        copywriter: Optional[LeaflyCopywriter] = None,
        translator: Optional[OpenAITranslator] = None,
        taxonomy_translator: Optional[TaxonomyTranslator] = None,
    ):
        self.reporter = reporter
        self.client = client or LeaflyClient()
        self.parser = parser or LeaflyParser()
        self.copywriter = copywriter or LeaflyCopywriter()
        self.translator = translator or OpenAITranslator()
        self.taxonomy_translator = taxonomy_translator or TaxonomyTranslator()
        self.persister = StrainPersister(self.taxonomy_translator, reporter=reporter)

    def import_alias(self, alias: str, dry_run: bool = False) -> str:
        alias = alias.strip()
        if not alias:
            return 'skipped'

        if self._exists_by_name_or_alias(alias):
            self.reporter.warning('check', f'Skipping {alias} (already exists)')
            return 'skipped'

        try:
            html = self.client.fetch(alias)
            self.reporter.success('fetch', f'Fetched {alias}')
        except LeaflyFetchError as exc:
            self.reporter.error('fetch', f'{alias} - {exc}')
            return 'failed'

        try:
            parsed = self.parser.parse(html)
            self.reporter.success('parse', f'Parsed {parsed.name}')
        except LeaflyParseError as exc:
            self.reporter.error('parse', f'{alias} - {exc}')
            return 'failed'

        if self._exists_by_name_or_alias(parsed.name):
            self.reporter.warning('check', f'Skipping {parsed.name} (already exists)')
            return 'skipped'

        try:
            copywriting = self.copywriter.rewrite(parsed)
            self.reporter.success('copy', f'Copywritten {parsed.name}')
        except CopywritingError as exc:
            self.reporter.error('copy', f'{parsed.name} - {exc}')
            return 'failed'

        if self._exists_by_name_or_alias_list(copywriting.get('alternative_names', [])):
            self.reporter.warning(
                'check',
                f'Skipping {parsed.name} (alternative name already exists)',
            )
            return 'skipped'

        translations = {}
        try:
            translations = self._translate_fields(copywriting)
            self.reporter.success('translate', f'Translated {parsed.name}')
        except TranslationError as exc:
            self.reporter.error('translate', f'{parsed.name} - {exc}')
            return 'failed'

        if dry_run:
            self.reporter.info('save', f'Dry run - skipping save for {parsed.name}')
            return 'dry-run'

        try:
            strain = self.persister.persist(parsed, copywriting, translations)
            self.reporter.success('save', f'Saved {strain.name} (ID {strain.id})')
        except Exception as exc:
            self.reporter.error('save', f'{parsed.name} - {exc}')
            return 'failed'

        return 'created'

    def _translate_fields(self, copywriting: Dict[str, object]) -> Dict[str, str]:
        fields = {
            'text_content': copywriting['text_content'],
            'img_alt_text': copywriting['img_alt_text'],
        }
        return self.translator.translate('Strain', fields, 'en', 'es')

    def _exists_by_name_or_alias(self, name: str) -> bool:
        if Strain.objects.filter(name__iexact=name).exists():
            return True
        if AlternativeStrainName.objects.filter(name__iexact=name).exists():
            return True
        return False

    def _exists_by_name_or_alias_list(self, names: Iterable[str]) -> bool:
        for name in names:
            if self._exists_by_name_or_alias(name):
                return True
        return False
