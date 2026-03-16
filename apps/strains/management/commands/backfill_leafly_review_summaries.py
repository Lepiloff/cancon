import time
from typing import List

from django.core.management.base import BaseCommand, CommandError
from django.db.models import Q
from django.template.defaultfilters import slugify

from apps.strains.leafly_import import (
    LeaflyClient,
    LeaflyParser,
    LeaflyReviewSummaryService,
)
from apps.strains.models import Strain


class CommandReporter:
    def __init__(self, stdout, style):
        self.stdout = stdout
        self.style = style

    def success(self, stage: str, message: str):
        self.stdout.write(self.style.SUCCESS(self._format(stage, message)))

    def warning(self, stage: str, message: str):
        self.stdout.write(self.style.WARNING(self._format(stage, message)))

    def error(self, stage: str, message: str):
        self.stdout.write(self.style.ERROR(self._format(stage, message)))

    def info(self, stage: str, message: str):
        self.stdout.write(self._format(stage, message))

    def _format(self, stage: str, message: str) -> str:
        return f'[{stage}] {message}'


class Command(BaseCommand):
    help = 'Backfill Leafly review summaries for active strains'

    def add_arguments(self, parser):
        parser.add_argument(
            'strain_slugs',
            nargs='*',
            help='Local strain slugs to process. If omitted, all matching active strains are processed.',
        )
        parser.add_argument(
            '--pause',
            type=float,
            default=5.0,
            help='Delay in seconds between strains (default: 5.0)',
        )
        parser.add_argument(
            '--timeout',
            type=int,
            default=15,
            help='HTTP timeout in seconds (default: 15)',
        )
        parser.add_argument(
            '--retries',
            type=int,
            default=2,
            help='Number of retries for Leafly requests (default: 2)',
        )
        parser.add_argument(
            '--limit',
            type=int,
            default=0,
            help='Process at most N strains (0 = no limit)',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Generate summaries without saving them',
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Process active strains even if review summaries are already filled',
        )

    def handle(self, *args, **options):
        reporter = CommandReporter(self.stdout, self.style)
        strains = self._collect_strains(options)
        if not strains:
            reporter.info('done', 'No matching strains found')
            return

        client = LeaflyClient(timeout=options['timeout'], retries=options['retries'])
        parser = LeaflyParser()
        try:
            review_service = LeaflyReviewSummaryService(
                reporter=reporter,
                client=client,
                parser=parser,
            )
        except Exception as exc:
            raise CommandError(str(exc)) from exc

        total = len(strains)
        results = {'updated': 0, 'missing': 0, 'failed': 0, 'dry-run': 0}

        for index, strain in enumerate(strains, start=1):
            candidates = self._build_alias_candidates(strain)
            reporter.info(
                'start',
                f'[{index}/{total}] {strain.slug} -> {", ".join(candidates)}',
            )

            summary = None
            matched_alias = None
            for alias in candidates:
                summary = review_service.fetch_summary(alias, strain.name)
                if summary:
                    matched_alias = alias
                    break

            if not summary:
                reporter.warning(
                    'match',
                    f'{strain.slug}: no matching Leafly review page or usable reviews found',
                )
                results['missing'] += 1
            elif options['dry_run']:
                reporter.info(
                    'save',
                    f'Dry run - would save review summary for {strain.slug} using alias {matched_alias}',
                )
                results['dry-run'] += 1
            else:
                try:
                    strain.review_summary_en = summary.get('en', '')
                    strain.review_summary_es = summary.get('es', '')
                    strain.save(update_fields=['review_summary_en', 'review_summary_es'])
                    reporter.success(
                        'save',
                        f'Saved review summary for {strain.slug} using alias {matched_alias}',
                    )
                    results['updated'] += 1
                except Exception as exc:
                    reporter.error('save', f'{strain.slug}: {exc}')
                    results['failed'] += 1

            if index < total and options['pause'] > 0:
                time.sleep(options['pause'])

        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('Backfill summary'))
        self.stdout.write(f"Updated: {results['updated']}")
        self.stdout.write(f"Missing: {results['missing']}")
        self.stdout.write(f"Failed:  {results['failed']}")
        if options['dry_run']:
            self.stdout.write(f"Dry-run: {results['dry-run']}")

    def _collect_strains(self, options) -> List[Strain]:
        queryset = (
            Strain.objects.filter(active=True)
            .prefetch_related('alternative_names')
            .order_by('id')
        )

        requested_slugs = [slug.strip() for slug in options['strain_slugs'] if slug.strip()]
        if requested_slugs:
            queryset = queryset.filter(slug__in=requested_slugs)

        if not options['force']:
            queryset = queryset.filter(
                Q(review_summary_en__isnull=True)
                | Q(review_summary_en='')
                | Q(review_summary_es__isnull=True)
                | Q(review_summary_es='')
            )

        limit = options['limit']
        if limit > 0:
            queryset = queryset[:limit]

        return list(queryset)

    def _build_alias_candidates(self, strain: Strain) -> List[str]:
        candidates = []
        raw_candidates = [strain.slug, slugify(strain.name)]
        raw_candidates.extend(slugify(name) for name in strain.alternative_names.values_list('name', flat=True))

        seen = set()
        for alias in raw_candidates:
            alias = (alias or '').strip().lower()
            if not alias or alias in seen:
                continue
            seen.add(alias)
            candidates.append(alias)
        return candidates
