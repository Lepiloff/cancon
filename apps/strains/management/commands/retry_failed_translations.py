"""
Retry Failed Translations

Manually retry translations that failed.
"""

import logging
from django.core.management.base import BaseCommand

from apps.strains.models import Strain, Article, Terpene
from apps.strains.signals import perform_translation

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = """Retry failed translations

    This command finds all objects with translation_status='failed' and retries them.

    Examples:
        # Retry up to 100 failed translations
        python manage.py retry_failed_translations --max 100

        # Retry only Strain failures
        python manage.py retry_failed_translations --model Strain
    """

    def add_arguments(self, parser):
        parser.add_argument(
            '--max',
            type=int,
            default=100,
            help='Maximum number of failed translations to retry (default: 100)',
        )
        parser.add_argument(
            '--model',
            type=str,
            choices=['Strain', 'Article', 'Terpene', 'all'],
            default='all',
            help='Which model to retry (default: all)',
        )

    def handle(self, *args, **options):
        max_retries = options['max']
        model_choice = options['model']

        models_to_process = {
            'Strain': Strain,
            'Article': Article,
            'Terpene': Terpene,
        }

        if model_choice != 'all':
            models_to_process = {model_choice: models_to_process[model_choice]}

        self.stdout.write('=' * 70)
        self.stdout.write(self.style.SUCCESS('Retrying Failed Translations'))
        self.stdout.write('=' * 70)
        self.stdout.write('')

        total_retried = 0
        total_succeeded = 0
        total_failed = 0

        for model_name, ModelClass in models_to_process.items():
            self.stdout.write(self.style.HTTP_INFO(f'\n{model_name}:'))
            self.stdout.write('-' * 70)

            # Get failed objects
            failed_objects = ModelClass.objects.filter(
                translation_status='failed'
            )[:max_retries]

            count = failed_objects.count()

            if count == 0:
                self.stdout.write(
                    self.style.WARNING(f'  No failed {model_name} translations')
                )
                continue

            self.stdout.write(f'  Found {count} failed translations')

            # Retry each one
            for idx, obj in enumerate(failed_objects, 1):
                identifier = getattr(obj, 'name', None) or getattr(
                    obj, 'title', f'ID {obj.id}'
                )

                self.stdout.write(
                    f'  [{idx}/{count}] Retrying: {identifier}...',
                    ending='',
                )
                self.stdout.flush()

                success = perform_translation(obj, model_name)

                self.stdout.write(
                    '\r' + ' ' * 100 + '\r', ending=''
                )  # Clear line

                if success:
                    self.stdout.write(
                        f'  [{idx}/{count}] '
                        + self.style.SUCCESS(f'✓ Succeeded: {identifier}')
                    )
                    total_succeeded += 1
                else:
                    self.stdout.write(
                        f'  [{idx}/{count}] '
                        + self.style.ERROR(f'✗ Failed again: {identifier}')
                    )
                    total_failed += 1

                total_retried += 1

            self.stdout.write('')
            self.stdout.write(self.style.SUCCESS(f'  ✓ Succeeded: {total_succeeded}'))
            if total_failed > 0:
                self.stdout.write(self.style.ERROR(f'  ✗ Failed: {total_failed}'))

        # Final summary
        self.stdout.write('')
        self.stdout.write('=' * 70)
        self.stdout.write(self.style.SUCCESS('SUMMARY'))
        self.stdout.write('=' * 70)
        self.stdout.write(f'Total retried: {total_retried}')
        self.stdout.write(self.style.SUCCESS(f'Succeeded: {total_succeeded}'))
        if total_failed > 0:
            self.stdout.write(self.style.ERROR(f'Failed again: {total_failed}'))
