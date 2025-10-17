from django.core.management.base import BaseCommand
from django.db.models import Count
from apps.strains.models import Strain, Article, Terpene


class Command(BaseCommand):
    help = 'Check translation status across all models'

    def add_arguments(self, parser):
        parser.add_argument(
            '--fix',
            action='store_true',
            help='Automatically queue outdated translations',
        )
        parser.add_argument(
            '--model',
            type=str,
            choices=['Strain', 'Article', 'Terpene', 'all'],
            default='all',
            help='Which model to check',
        )

    def handle(self, *args, **options):
        models_to_check = {
            'Strain': Strain,
            'Article': Article,
            'Terpene': Terpene,
        }

        if options['model'] != 'all':
            models_to_check = {options['model']: models_to_check[options['model']]}

        self.stdout.write(self.style.SUCCESS('Translation Status Report'))
        self.stdout.write('=' * 70)

        total_needs_translation = 0

        for model_name, Model in models_to_check.items():
            self.stdout.write(f'\n{model_name}:')

            total = Model.objects.count()
            status_counts = Model.objects.values('translation_status').annotate(
                count=Count('id')
            )

            self.stdout.write(f'  Total: {total}')
            for status in status_counts:
                status_display = status['translation_status'] or 'None'
                self.stdout.write(
                    f"  {status_display}: {status['count']}"
                )

            # Check for objects that need translation
            needs_translation = []
            for obj in Model.objects.all():
                if obj.needs_translation():
                    needs_translation.append(obj)

            if needs_translation:
                total_needs_translation += len(needs_translation)
                self.stdout.write(
                    self.style.WARNING(
                        f'  ⚠ {len(needs_translation)} objects need translation'
                    )
                )

                if options['fix']:
                    for obj in needs_translation:
                        obj.mark_translation_pending()

                    self.stdout.write(
                        self.style.SUCCESS(
                            f'  ✓ Queued {len(needs_translation)} objects for translation'
                        )
                    )

        self.stdout.write('\n' + '=' * 70)
        self.stdout.write(
            self.style.SUCCESS(
                f'\nTotal objects needing translation: {total_needs_translation}'
            )
        )

        if total_needs_translation > 0 and not options['fix']:
            self.stdout.write(
                self.style.WARNING(
                    '\nRun with --fix to automatically queue these for translation'
                )
            )
