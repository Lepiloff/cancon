from django.core.management.base import BaseCommand
from apps.strains.models import Feeling, Negative, HelpsWith, Flavor, Terpene
from apps.strains.localizations import (
    feelings_translation,
    negatives_translator,
    helps_with_translation,
    flavors_translation,
)


class Command(BaseCommand):
    help = '''Populate English translations for taxonomy models and fix Spanish translations.

    This command:
    1. Sets English as primary (name_en) for Feelings, Flavors, Negatives, HelpsWith
    2. Uses localizations.py mappings for Spanish translations (name_es)
    3. Fixes Terpene names to English (removes Spanish)

    Run with --dry-run first to see what will be changed.
    '''

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be done without making changes',
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Overwrite existing translations',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        force = options['force']

        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN MODE - No changes will be made'))

        self.stdout.write('=' * 70)
        self.stdout.write(self.style.SUCCESS('Populating Translations'))
        self.stdout.write('=' * 70)

        # Process each model
        self.process_feelings(dry_run, force)
        self.process_negatives(dry_run, force)
        self.process_helps_with(dry_run, force)
        self.process_flavors(dry_run, force)
        self.process_terpenes(dry_run, force)

        self.stdout.write('=' * 70)
        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN COMPLETED - Run without --dry-run to apply changes'))
        else:
            self.stdout.write(self.style.SUCCESS('COMPLETED - All translations updated'))

    def process_feelings(self, dry_run, force):
        """Process Feeling model"""
        self.stdout.write('\n' + self.style.HTTP_INFO('Processing Feelings...'))

        # Reverse mapping: Spanish -> English
        spanish_to_english = {v: k for k, v in feelings_translation.items()}

        updated = 0
        skipped = 0

        for feeling in Feeling.objects.all():
            current_name_es = feeling.name_es or ''
            current_name_en = feeling.name_en or ''

            # Try to find English equivalent
            english_name = spanish_to_english.get(current_name_es, current_name_es)
            spanish_name = feelings_translation.get(english_name, current_name_es)

            should_update = False
            changes = []

            # Check if we need to update EN
            if not current_name_en or force:
                if english_name != current_name_en:
                    should_update = True
                    changes.append(f"EN: '{current_name_en}' -> '{english_name}'")

            # Check if we need to update ES
            if not current_name_es or force:
                if spanish_name != current_name_es:
                    should_update = True
                    changes.append(f"ES: '{current_name_es}' -> '{spanish_name}'")

            if should_update:
                self.stdout.write(f"  Feeling #{feeling.id}: {' | '.join(changes)}")

                if not dry_run:
                    feeling.name_en = english_name
                    feeling.name_es = spanish_name
                    feeling.save()

                updated += 1
            else:
                skipped += 1

        self.stdout.write(self.style.SUCCESS(f"  ✓ Updated: {updated}, Skipped: {skipped}"))

    def process_negatives(self, dry_run, force):
        """Process Negative model"""
        self.stdout.write('\n' + self.style.HTTP_INFO('Processing Negatives...'))

        spanish_to_english = {v: k for k, v in negatives_translator.items()}

        updated = 0
        skipped = 0

        for negative in Negative.objects.all():
            current_name_es = negative.name_es or ''
            current_name_en = negative.name_en or ''

            english_name = spanish_to_english.get(current_name_es, current_name_es)
            spanish_name = negatives_translator.get(english_name, current_name_es)

            should_update = False
            changes = []

            if not current_name_en or force:
                if english_name != current_name_en:
                    should_update = True
                    changes.append(f"EN: '{current_name_en}' -> '{english_name}'")

            if not current_name_es or force:
                if spanish_name != current_name_es:
                    should_update = True
                    changes.append(f"ES: '{current_name_es}' -> '{spanish_name}'")

            if should_update:
                self.stdout.write(f"  Negative #{negative.id}: {' | '.join(changes)}")

                if not dry_run:
                    negative.name_en = english_name
                    negative.name_es = spanish_name
                    negative.save()

                updated += 1
            else:
                skipped += 1

        self.stdout.write(self.style.SUCCESS(f"  ✓ Updated: {updated}, Skipped: {skipped}"))

    def process_helps_with(self, dry_run, force):
        """Process HelpsWith model"""
        self.stdout.write('\n' + self.style.HTTP_INFO('Processing HelpsWith...'))

        spanish_to_english = {v: k for k, v in helps_with_translation.items()}

        updated = 0
        skipped = 0

        for helps_with in HelpsWith.objects.all():
            current_name_es = helps_with.name_es or ''
            current_name_en = helps_with.name_en or ''

            english_name = spanish_to_english.get(current_name_es, current_name_es)
            spanish_name = helps_with_translation.get(english_name, current_name_es)

            should_update = False
            changes = []

            if not current_name_en or force:
                if english_name != current_name_en:
                    should_update = True
                    changes.append(f"EN: '{current_name_en}' -> '{english_name}'")

            if not current_name_es or force:
                if spanish_name != current_name_es:
                    should_update = True
                    changes.append(f"ES: '{current_name_es}' -> '{spanish_name}'")

            if should_update:
                self.stdout.write(f"  HelpsWith #{helps_with.id}: {' | '.join(changes)}")

                if not dry_run:
                    helps_with.name_en = english_name
                    helps_with.name_es = spanish_name
                    helps_with.save()

                updated += 1
            else:
                skipped += 1

        self.stdout.write(self.style.SUCCESS(f"  ✓ Updated: {updated}, Skipped: {skipped}"))

    def process_flavors(self, dry_run, force):
        """Process Flavor model"""
        self.stdout.write('\n' + self.style.HTTP_INFO('Processing Flavors...'))

        spanish_to_english = {v: k for k, v in flavors_translation.items()}

        updated = 0
        skipped = 0
        not_found = []

        for flavor in Flavor.objects.all():
            current_name_es = flavor.name_es or ''
            current_name_en = flavor.name_en or ''

            # Current name might be in English already
            # First check if current ES value has translation
            if current_name_es.lower() in [k.lower() for k in spanish_to_english.keys()]:
                # It's Spanish, find English
                english_name = spanish_to_english.get(current_name_es, current_name_es)
                spanish_name = current_name_es
            elif current_name_es.lower() in [k.lower() for k in flavors_translation.keys()]:
                # It's English, find Spanish
                english_name = current_name_es
                spanish_name = flavors_translation.get(current_name_es, current_name_es)
            else:
                # Not found in translations, keep as is
                english_name = current_name_es
                spanish_name = current_name_es
                not_found.append(current_name_es)

            should_update = False
            changes = []

            if not current_name_en or force:
                if english_name != current_name_en:
                    should_update = True
                    changes.append(f"EN: '{current_name_en}' -> '{english_name}'")

            if not current_name_es or (force and english_name != spanish_name):
                if spanish_name != current_name_es:
                    should_update = True
                    changes.append(f"ES: '{current_name_es}' -> '{spanish_name}'")

            if should_update:
                self.stdout.write(f"  Flavor #{flavor.id}: {' | '.join(changes)}")

                if not dry_run:
                    flavor.name_en = english_name
                    flavor.name_es = spanish_name
                    flavor.save()

                updated += 1
            else:
                skipped += 1

        if not_found:
            self.stdout.write(self.style.WARNING(f"  ⚠ Not found in translations: {', '.join(set(not_found))}"))

        self.stdout.write(self.style.SUCCESS(f"  ✓ Updated: {updated}, Skipped: {skipped}"))

    def process_terpenes(self, dry_run, force):
        """Fix Terpene names to English"""
        self.stdout.write('\n' + self.style.HTTP_INFO('Processing Terpenes (fixing to English)...'))

        # Spanish -> English mapping for terpenes
        terpene_fixes = {
            'Humuleno': 'Humulene',
            'Ocimeno': 'Ocimene',
            'Terpinoleno': 'Terpinolene',
            'Pineno': 'Pinene',
            'Mirceno': 'Myrcene',
            'Limoneno': 'Limonene',
            'Cariofileno': 'Caryophyllene',
            'Linalool': 'Linalool',  # Already correct
        }

        updated = 0
        skipped = 0

        for terpene in Terpene.objects.all():
            current_name = terpene.name

            # Check if name needs fixing
            english_name = None
            for spanish, english in terpene_fixes.items():
                if spanish.lower() in current_name.lower():
                    # Replace Spanish with English, keep any extra info like "(floral)"
                    english_name = current_name.replace(spanish, english).replace(spanish.lower(), english)
                    break

            if english_name and english_name != current_name:
                self.stdout.write(f"  Terpene #{terpene.id}: '{current_name}' -> '{english_name}'")

                if not dry_run:
                    terpene.name = english_name
                    terpene.save()

                updated += 1
            else:
                skipped += 1

        self.stdout.write(self.style.SUCCESS(f"  ✓ Updated: {updated}, Skipped: {skipped}"))
