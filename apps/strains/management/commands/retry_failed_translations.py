from django.core.management.base import BaseCommand
from apps.strains.models import Strain, Article, Terpene
from apps.strains.signals import send_to_translation_queue


class Command(BaseCommand):
    help = 'Retry failed translations'

    def add_arguments(self, parser):
        parser.add_argument(
            '--max',
            type=int,
            default=100,
            help='Maximum number of failed translations to retry',
        )

    def handle(self, *args, **options):
        models = {
            'Strain': Strain,
            'Article': Article,
            'Terpene': Terpene,
        }

        total_retried = 0

        for model_name, Model in models.items():
            failed = Model.objects.filter(translation_status='failed')[
                :options['max']
            ]

            if not failed:
                self.stdout.write(f'{model_name}: No failed translations')
                continue

            for obj in failed:
                fields = obj.get_translatable_fields()
                if fields:
                    fields['content_hash'] = obj.get_translatable_content_hash()
                    success = send_to_translation_queue(
                        model_name, obj.id, fields
                    )
                    if success:
                        obj.translation_status = 'pending'
                        obj.save(update_fields=['translation_status'])
                        total_retried += 1

            self.stdout.write(
                self.style.SUCCESS(
                    f'{model_name}: Retried {failed.count()} failed translations'
                )
            )

        self.stdout.write(
            self.style.SUCCESS(f'\nTotal retried: {total_retried}')
        )
