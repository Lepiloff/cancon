import time
from typing import List

from django.core.management.base import BaseCommand, CommandError

from apps.strains.leafly_import import LeaflyClient, LeaflyImporter


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
    help = 'Import strains from Leafly by alias list'

    def add_arguments(self, parser):
        parser.add_argument(
            'aliases',
            nargs='*',
            help='Leafly strain aliases (URL slugs)',
        )
        parser.add_argument(
            '--alias-file',
            type=str,
            help='Path to a file with one alias per line',
        )
        parser.add_argument(
            '--pause',
            type=float,
            default=5.0,
            help='Delay in seconds between Leafly requests (default: 5.0)',
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
            '--dry-run',
            action='store_true',
            help='Run without saving to the database',
        )

    def handle(self, *args, **options):
        aliases = self._collect_aliases(options)
        if not aliases:
            raise CommandError('No aliases provided')

        reporter = CommandReporter(self.stdout, self.style)
        client = LeaflyClient(timeout=options['timeout'], retries=options['retries'])
        try:
            importer = LeaflyImporter(reporter, client=client)
        except Exception as exc:
            raise CommandError(str(exc)) from exc

        total = len(aliases)
        results = {'created': 0, 'failed': 0, 'skipped': 0, 'dry-run': 0}

        for index, alias in enumerate(aliases, start=1):
            reporter.info('start', f'[{index}/{total}] Importing {alias}')
            outcome = importer.import_alias(alias, dry_run=options['dry_run'])
            results[outcome] = results.get(outcome, 0) + 1

            if index < total and options['pause'] > 0:
                time.sleep(options['pause'])

        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('Import summary'))
        self.stdout.write(f"Created: {results['created']}")
        self.stdout.write(f"Skipped: {results['skipped']}")
        self.stdout.write(f"Failed: {results['failed']}")
        if options['dry_run']:
            self.stdout.write(f"Dry-run: {results['dry-run']}")

    def _collect_aliases(self, options) -> List[str]:
        aliases = list(options['aliases'])
        alias_file = options.get('alias_file')
        if alias_file:
            aliases.extend(self._read_alias_file(alias_file))
        return self._dedupe([alias.strip() for alias in aliases if alias.strip()])

    def _read_alias_file(self, path: str) -> List[str]:
        try:
            with open(path, 'r') as handle:
                return [
                    line.strip()
                    for line in handle
                    if line.strip() and not line.strip().startswith('#')
                ]
        except OSError as exc:
            raise CommandError(f'Failed to read alias file: {exc}') from exc

    def _dedupe(self, aliases: List[str]) -> List[str]:
        seen = set()
        ordered = []
        for alias in aliases:
            key = alias.lower()
            if key in seen:
                continue
            seen.add(key)
            ordered.append(alias)
        return ordered
