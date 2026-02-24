import json
import re
import time
from typing import Dict, List, Optional, Set, Tuple

from bs4 import BeautifulSoup
from openai import OpenAI, OpenAIError

from django.core.management.base import BaseCommand, CommandError

from apps.strains.models import AlternativeStrainName, Strain
from apps.translation.config import TranslationConfig

SYSTEM_PROMPT = """You are a cannabis genetics expert. You analyze strain descriptions and extract genetic lineage information.
Return ONLY valid JSON, no explanations."""

USER_PROMPT_TEMPLATE = """Analyze the following cannabis strain description and extract:

1. "parent_strains": List of strain names that are GENETIC PARENTS/ANCESTORS of this strain.
   Include ONLY strains explicitly described as parents, crosses, genetic origins, or ancestors.
   Do NOT include strains mentioned as alternatives, recommendations, or similar experiences.

2. "mentioned_strains": List of ALL other cannabis strain names mentioned in the text,
   INCLUDING the parent strains AND strains mentioned as alternatives/recommendations.
   Do NOT include the strain itself ("{strain_name}").

EXAMPLES:

Example 1 — strain "9 lb Hammer":
Text: "In the realm of cultivation, this strain, the result of the genetic combination between Gooberry, Hells OG, and Jack the Ripper, stands out for its rapid flowering."
Answer: {{"parent_strains": ["Gooberry", "Hells OG", "Jack the Ripper"], "mentioned_strains": ["Gooberry", "Hells OG", "Jack the Ripper"]}}
Reasoning: "genetic combination between" clearly indicates these are parent strains.

Example 2 — strain "Alien OG":
Text: "Alien OG, a descendant of the renowned strains Tahoe OG and Alien Kush, is a hybrid that offers the best of both Indica and Sativa worlds."
Answer: {{"parent_strains": ["Tahoe OG", "Alien Kush"], "mentioned_strains": ["Tahoe OG", "Alien Kush"]}}
Reasoning: "descendant of" indicates genetic parentage.

Example 3 — strain "ACDC":
Text: "If you have been fascinated by the balanced experience that ACDC offers, you will likely also enjoy the strains Charlotte's Web and Harlequin, both renowned for their high CBD content."
Answer: {{"parent_strains": [], "mentioned_strains": ["Charlotte's Web", "Harlequin"]}}
Reasoning: "you will likely also enjoy" means these are recommendations, NOT parents.

Example 4 — strain "Acapulco Gold":
Text: "If you love the energizing effect of Acapulco Gold, strains like Green Crack and Sour Diesel also offer a similar experience of vitality and creativity."
Answer: {{"parent_strains": [], "mentioned_strains": ["Green Crack", "Sour Diesel"]}}
Reasoning: "strains like ... also offer a similar experience" means alternatives, NOT parents.

Return JSON only:
{{
  "parent_strains": ["Parent1", "Parent2"],
  "mentioned_strains": ["Parent1", "Parent2", "Alternative1", "Alternative2"]
}}

If no parent strains are found, return empty list for "parent_strains".
If no strains are mentioned at all, return empty lists for both.

Strain name: {strain_name}
Description:
{text_content}"""


def _strip_html(html: str) -> str:
    """Strip HTML tags, returning plain text for LLM analysis."""
    soup = BeautifulSoup(html, 'html.parser')
    return soup.get_text(separator=' ', strip=True)


def _strip_code_fences(content: str) -> str:
    """Remove markdown code fences from LLM response."""
    if content.startswith('```'):
        lines = content.split('\n')
        lines = lines[1:]
        if lines and lines[-1].strip() == '```':
            lines = lines[:-1]
        return '\n'.join(lines).strip()
    return content


def _find_strain_by_name(name: str) -> Optional[Strain]:
    """Find a strain by exact name or alternative name (case-insensitive)."""
    strain = Strain.objects.filter(name__iexact=name).first()
    if strain:
        return strain
    alt = AlternativeStrainName.objects.filter(name__iexact=name).select_related('strain').first()
    if alt:
        return alt.strain
    return None


def _is_already_linked(text: str, name: str) -> bool:
    """Check if a strain name is already wrapped in an <a> tag in the text."""
    pattern = re.compile(
        r'<a\b[^>]*>' + re.escape(name) + r'</a>',
        re.IGNORECASE,
    )
    return bool(pattern.search(text))


def _add_link(text: str, name: str, slug: str, lang: str) -> Tuple[str, bool]:
    """
    Replace the first occurrence of `name` in `text` with an HTML link.
    Returns (new_text, was_replaced).
    Skips if already linked.
    """
    if not text or not name:
        return text, False

    if _is_already_linked(text, name):
        return text, False

    if lang == 'en':
        href = f'/en/strain/{slug}/'
    else:
        href = f'/strain/{slug}/'

    # Word-boundary match, case-insensitive, first occurrence only
    pattern = re.compile(
        r'(?<![<>/\w])(' + re.escape(name) + r')(?![<\w])',
        re.IGNORECASE,
    )
    new_text, count = pattern.subn(
        f'<a href="{href}">\\1</a>',
        text,
        count=1,
    )
    return new_text, count > 0


class Command(BaseCommand):
    help = 'Extract parent strain genetics from descriptions using LLM and add internal links'

    def add_arguments(self, parser):
        parser.add_argument(
            '--limit', type=int, default=0,
            help='Process at most N strains (0 = no limit)',
        )
        parser.add_argument(
            '--dry-run', action='store_true',
            help='Show what would be done without saving to DB',
        )
        parser.add_argument(
            '--pause', type=float, default=1.0,
            help='Pause between LLM calls in seconds (default: 1.0)',
        )
        parser.add_argument(
            '--strain', type=str,
            help='Process a specific strain by name',
        )
        parser.add_argument(
            '--force', action='store_true',
            help='Process strains even if they already have parents',
        )

    def handle(self, *args, **options):
        TranslationConfig.validate()
        self.client = OpenAI(
            api_key=TranslationConfig.OPENAI_API_KEY,
            timeout=TranslationConfig.OPENAI_TIMEOUT,
        )
        self.model = TranslationConfig.OPENAI_MODEL
        self.dry_run = options['dry_run']

        strains = self._get_queryset(options)
        total = strains.count()

        if total == 0:
            self.stdout.write('No strains to process.')
            return

        self.stdout.write(f'Processing {total} strains (dry_run={self.dry_run})')

        stats = {
            'processed': 0,
            'parents_found': 0,
            'parents_not_in_db': 0,
            'links_added': 0,
            'errors': 0,
        }

        for index, strain in enumerate(strains.iterator(), start=1):
            try:
                self._process_strain(strain, index, total, stats)
            except Exception as exc:
                stats['errors'] += 1
                self.stdout.write(self.style.ERROR(
                    f'[{index}/{total}] {strain.name} — ERROR: {exc}'
                ))

            stats['processed'] += 1

            if index < total and options['pause'] > 0:
                time.sleep(options['pause'])

        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('Summary:'))
        self.stdout.write(f"  Total processed: {stats['processed']}")
        self.stdout.write(f"  Parents found:   {stats['parents_found']}")
        self.stdout.write(f"  Parents not in DB: {stats['parents_not_in_db']}")
        self.stdout.write(f"  Links added:     {stats['links_added']}")
        self.stdout.write(f"  Errors:          {stats['errors']}")

    def _get_queryset(self, options):
        if options['strain']:
            qs = Strain.objects.filter(name__iexact=options['strain'])
            if not qs.exists():
                raise CommandError(f"Strain not found: {options['strain']}")
            return qs

        qs = Strain.objects.all()
        if not options['force']:
            qs = qs.filter(parents__isnull=True)
        qs = qs.order_by('name')

        if options['limit'] > 0:
            qs = qs[:options['limit']]
        return qs

    def _process_strain(self, strain: Strain, index: int, total: int, stats: Dict):
        text_en = strain.text_content_en or ''
        plain_text = _strip_html(text_en)

        if len(plain_text) < 50:
            self.stdout.write(f'[{index}/{total}] {strain.name} — skipped (text too short)')
            return

        # Call LLM
        data = self._call_llm(strain.name, plain_text)
        parent_names = data.get('parent_strains', [])
        mentioned_names = data.get('mentioned_strains', [])

        # --- Parents ---
        found_parents = []
        not_found = []
        for name in parent_names:
            parent = _find_strain_by_name(name)
            if parent and parent.pk != strain.pk:
                found_parents.append(parent)
            else:
                not_found.append(name)

        if found_parents and not self.dry_run:
            strain.parents.add(*found_parents)

        stats['parents_found'] += len(found_parents)
        stats['parents_not_in_db'] += len(not_found)

        if found_parents or not_found:
            parent_str = ', '.join(p.name for p in found_parents) if found_parents else 'none'
            self.stdout.write(
                f'[{index}/{total}] {strain.name}\n'
                f'  [parents] {parent_str} '
                f'({len(found_parents)} found, {len(not_found)} not in DB)'
            )
        else:
            self.stdout.write(f'[{index}/{total}] {strain.name}\n  [parents] none found')

        # --- Links ---
        # Collect all mentioned strains that exist in DB (excluding self)
        link_targets: List[Tuple[str, Strain]] = []
        seen_pks: Set[int] = set()
        for name in mentioned_names:
            target = _find_strain_by_name(name)
            if target and target.pk != strain.pk and target.pk not in seen_pks:
                link_targets.append((name, target))
                seen_pks.add(target.pk)

        # Sort by name length descending so longer names are linked first,
        # preventing partial matches (e.g. "Harlequin" inside "Harlequin GDP")
        link_targets.sort(key=lambda x: len(x[0]), reverse=True)

        en_links = 0
        es_links = 0

        text_en_updated = strain.text_content_en or ''
        text_es_updated = strain.text_content_es or ''

        for name, target in link_targets:
            text_en_updated, added = _add_link(text_en_updated, name, target.slug, 'en')
            if added:
                en_links += 1

            # For ES text, search with the same name (English name in Spanish text)
            text_es_updated, added = _add_link(text_es_updated, name, target.slug, 'es')
            if added:
                es_links += 1

        if (en_links > 0 or es_links > 0) and not self.dry_run:
            strain.text_content_en = text_en_updated
            strain.text_content_es = text_es_updated
            strain.save(update_fields=['text_content_en', 'text_content_es'])

        stats['links_added'] += en_links + es_links

        linked_names = [name for name, _ in link_targets[:en_links]] if en_links else []
        self.stdout.write(f'  [links-en] {en_links} links added')
        self.stdout.write(f'  [links-es] {es_links} links added')

    def _call_llm(self, strain_name: str, text_content: str) -> Dict:
        prompt = USER_PROMPT_TEMPLATE.format(
            strain_name=strain_name,
            text_content=text_content,
        )

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.1,
                max_tokens=500,
            )
            content = response.choices[0].message.content.strip()
            content = _strip_code_fences(content)
            data = json.loads(content)

            if not isinstance(data.get('parent_strains'), list):
                data['parent_strains'] = []
            if not isinstance(data.get('mentioned_strains'), list):
                data['mentioned_strains'] = []

            return data
        except (OpenAIError, json.JSONDecodeError, KeyError, IndexError) as exc:
            raise RuntimeError(f'LLM call failed: {exc}') from exc
