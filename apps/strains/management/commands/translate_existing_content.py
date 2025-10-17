"""
Management command for bulk translation of existing content.

Phase 2: Translate all existing Spanish content to English (or vice versa).
Uses OpenAI API directly (no SQS/Lambda).
"""

import time
import logging
from typing import Dict, Type

from django.core.management.base import BaseCommand, CommandError
from django.db.models import Q, Model

from apps.strains.models import Strain, Article, Terpene
from apps.translation import OpenAITranslator, TranslationConfig
from apps.translation.base_translator import TranslationError

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = """Bulk translate existing content from one language to another.

    Examples:
        # Translate all Spanish content to English
        python manage.py translate_existing_content --direction es-to-en

        # Dry run to see what will be translated
        python manage.py translate_existing_content --direction es-to-en --dry-run

        # Translate only Strain model
        python manage.py translate_existing_content --direction es-to-en --model Strain

        # Limit to first 10 items (for testing)
        python manage.py translate_existing_content --direction es-to-en --limit 10
    """

    def add_arguments(self, parser):
        parser.add_argument(
            '--direction',
            type=str,
            required=True,
            choices=['es-to-en', 'en-to-es'],
            help='Translation direction (es-to-en or en-to-es)',
        )
        parser.add_argument(
            '--model',
            type=str,
            choices=['Strain', 'Article', 'Terpene', 'all'],
            default='all',
            help='Which model to translate (default: all)',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be translated without actually translating',
        )
        parser.add_argument(
            '--pause',
            type=float,
            default=TranslationConfig.DEFAULT_PAUSE_SECONDS,
            help=f'Pause between API calls in seconds (default: {TranslationConfig.DEFAULT_PAUSE_SECONDS})',
        )
        parser.add_argument(
            '--limit',
            type=int,
            help='Limit number of items to translate (for testing)',
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force retranslate even if target language already has content',
        )

    def handle(self, *args, **options):
        direction = options['direction']
        model_choice = options['model']
        dry_run = options['dry_run']
        pause = options['pause']
        limit = options['limit']
        force = options['force']

        # Parse direction
        source_lang, target_lang = TranslationConfig.parse_direction(direction)

        # Initialize translator
        try:
            translator = OpenAITranslator()
            if not dry_run:
                if not translator.validate_connection():
                    raise CommandError('Failed to validate OpenAI connection')
        except Exception as e:
            raise CommandError(f'Failed to initialize translator: {str(e)}')

        # Determine which models to process
        models_to_process = {
            'Strain': Strain,
            'Article': Article,
            'Terpene': Terpene,
        }

        if model_choice != 'all':
            models_to_process = {model_choice: models_to_process[model_choice]}

        # Display header
        self.stdout.write('=' * 70)
        self.stdout.write(
            self.style.SUCCESS(
                f'Bulk Translation: {source_lang.upper()} → {target_lang.upper()}'
            )
        )
        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN MODE - No translations will be performed'))
        self.stdout.write('=' * 70)
        self.stdout.write('')

        # Process each model
        total_translated = 0
        total_failed = 0
        total_skipped = 0

        for model_name, ModelClass in models_to_process.items():
            self.stdout.write(self.style.HTTP_INFO(f'\n{model_name}:'))
            self.stdout.write('-' * 70)

            # Get objects that need translation
            objects = self._get_objects_needing_translation(
                ModelClass, source_lang, target_lang, force, limit
            )

            total = objects.count()
            if total == 0:
                self.stdout.write(self.style.WARNING(f'  No {model_name} objects need translation'))
                continue

            self.stdout.write(f'  Found {total} objects to translate')
            if dry_run:
                self.stdout.write(self.style.WARNING(f'  Would translate {total} objects'))
                total_skipped += total
                continue

            # Process each object
            translated, failed, skipped = self._translate_objects(
                translator,
                objects,
                model_name,
                source_lang,
                target_lang,
                pause,
            )

            total_translated += translated
            total_failed += failed
            total_skipped += skipped

            # Summary for this model
            self.stdout.write('')
            self.stdout.write(self.style.SUCCESS(f'  ✓ Translated: {translated}'))
            if failed > 0:
                self.stdout.write(self.style.ERROR(f'  ✗ Failed: {failed}'))
            if skipped > 0:
                self.stdout.write(self.style.WARNING(f'  ⊘ Skipped: {skipped}'))

        # Final summary
        self.stdout.write('')
        self.stdout.write('=' * 70)
        self.stdout.write(self.style.SUCCESS('SUMMARY'))
        self.stdout.write('=' * 70)
        self.stdout.write(f'Total translated: {total_translated}')
        if total_failed > 0:
            self.stdout.write(self.style.ERROR(f'Total failed: {total_failed}'))
        if total_skipped > 0:
            self.stdout.write(f'Total skipped: {total_skipped}')

        if not dry_run and total_translated > 0:
            self.stdout.write('')
            self.stdout.write(
                self.style.SUCCESS(
                    '✓ Bulk translation completed! Check admin for results.'
                )
            )

    def _get_objects_needing_translation(
        self,
        ModelClass: Type[Model],
        source_lang: str,
        target_lang: str,
        force: bool,
        limit: int = None,
    ):
        """Get queryset of objects that need translation."""
        # Get translatable field names
        model_name = ModelClass.__name__
        field_names = TranslationConfig.get_model_fields(model_name)

        if not field_names:
            return ModelClass.objects.none()

        # Build query to find objects with source content but empty target
        query = Q()

        for field_name in field_names:
            source_field = f'{field_name}_{source_lang}'
            target_field = f'{field_name}_{target_lang}'

            if not hasattr(ModelClass, source_field):
                continue

            if force:
                # Force: any object with source content
                query |= Q(**{f'{source_field}__isnull': False}) & ~Q(**{f'{source_field}': ''})
            else:
                # Normal: source has content but target is empty
                query |= (
                    Q(**{f'{source_field}__isnull': False}) &
                    ~Q(**{f'{source_field}': ''}) &
                    (Q(**{f'{target_field}__isnull': True}) | Q(**{f'{target_field}': ''}))
                )

        queryset = ModelClass.objects.filter(query).distinct()

        if limit:
            queryset = queryset[:limit]

        return queryset

    def _translate_objects(
        self,
        translator: OpenAITranslator,
        objects,
        model_name: str,
        source_lang: str,
        target_lang: str,
        pause: float,
    ) -> tuple:
        """
        Translate a queryset of objects.

        Returns:
            Tuple of (translated_count, failed_count, skipped_count)
        """
        translated = 0
        failed = 0
        skipped = 0

        total = objects.count()

        for idx, obj in enumerate(objects, 1):
            # Progress indicator
            progress = f'[{idx}/{total}]'
            identifier = getattr(obj, 'name', None) or getattr(obj, 'title', f'ID {obj.id}')

            try:
                # Get fields to translate
                fields_to_translate = {}
                field_names = TranslationConfig.get_model_fields(model_name)

                for field_name in field_names:
                    source_field = f'{field_name}_{source_lang}'
                    if hasattr(obj, source_field):
                        content = getattr(obj, source_field, '')
                        if content:
                            fields_to_translate[field_name] = content

                if not fields_to_translate:
                    self.stdout.write(
                        f'  {progress} ⊘ Skipped: {identifier} (no source content)'
                    )
                    skipped += 1
                    continue

                # Translate
                self.stdout.write(
                    f'  {progress} ⟳ Translating: {identifier}...',
                    ending='',
                )
                self.stdout.flush()

                translations = translator.translate(
                    model_name,
                    fields_to_translate,
                    source_lang,
                    target_lang,
                )

                # Save translations
                for field_name, translated_text in translations.items():
                    target_field = f'{field_name}_{target_lang}'
                    if hasattr(obj, target_field):
                        setattr(obj, target_field, translated_text)

                # Save the object with translated fields
                obj.save()

                # Update translation metadata
                obj.mark_translation_synced()

                self.stdout.write('\r' + ' ' * 100 + '\r', ending='')  # Clear line
                self.stdout.write(
                    f'  {progress} ' +
                    self.style.SUCCESS(f'✓ Translated: {identifier}')
                )

                translated += 1

                # Pause to respect rate limits
                if idx < total:  # Don't pause after last item
                    time.sleep(pause)

            except TranslationError as e:
                self.stdout.write('\r' + ' ' * 100 + '\r', ending='')  # Clear line
                self.stdout.write(
                    f'  {progress} ' +
                    self.style.ERROR(f'✗ Failed: {identifier} - {str(e)}')
                )
                obj.mark_translation_failed(str(e))
                failed += 1

                # Continue with next object
                if idx < total:
                    time.sleep(pause)

            except Exception as e:
                self.stdout.write('\r' + ' ' * 100 + '\r', ending='')  # Clear line
                error_msg = f'Unexpected error: {str(e)}'
                self.stdout.write(
                    f'  {progress} ' +
                    self.style.ERROR(f'✗ Failed: {identifier} - {error_msg}')
                )
                obj.mark_translation_failed(error_msg)
                failed += 1

                if idx < total:
                    time.sleep(pause)

        return translated, failed, skipped
