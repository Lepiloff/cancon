"""
Management command to fix internal links in English translations.

Problem: After AI translation, English content contains links to Spanish URLs
without /en/ prefix. This script finds and corrects all internal links.

Example:
    English content has: <a href="/strain/northern-lights/">...</a>
    Should be: <a href="/en/strain/northern-lights/">...</a>

Usage:
    python manage.py fix_english_links
    python manage.py fix_english_links --dry-run
    python manage.py fix_english_links --model Strain
"""

import re
from django.core.management.base import BaseCommand
from django.db import transaction
from apps.strains.models import Strain, Article, Terpene


class Command(BaseCommand):
    help = 'Fix internal links in English translations to include /en/ prefix'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be changed without actually changing it',
        )
        parser.add_argument(
            '--model',
            type=str,
            choices=['Strain', 'Article', 'Terpene', 'all'],
            default='all',
            help='Which model to fix (default: all)',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        model_filter = options['model']

        if dry_run:
            self.stdout.write(self.style.WARNING('=' * 70))
            self.stdout.write(self.style.WARNING('DRY RUN MODE - No changes will be saved'))
            self.stdout.write(self.style.WARNING('=' * 70))

        models_to_fix = []
        if model_filter == 'all':
            models_to_fix = [Strain, Article, Terpene]
        else:
            model_map = {'Strain': Strain, 'Article': Article, 'Terpene': Terpene}
            models_to_fix = [model_map[model_filter]]

        total_objects_fixed = 0
        total_links_fixed = 0

        for model in models_to_fix:
            self.stdout.write(f'\n{self.style.HTTP_INFO(f"Processing {model.__name__}...")}')
            objects_fixed, links_fixed = self.fix_model_links(model, dry_run)
            total_objects_fixed += objects_fixed
            total_links_fixed += links_fixed

            if objects_fixed > 0:
                self.stdout.write(
                    self.style.SUCCESS(
                        f'✓ {model.__name__}: {objects_fixed} objects updated, {links_fixed} links fixed'
                    )
                )
            else:
                self.stdout.write(f'  {model.__name__}: No links to fix')

        self.stdout.write('')
        self.stdout.write('=' * 70)
        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    f'DRY RUN: Would fix {total_links_fixed} links in {total_objects_fixed} objects'
                )
            )
            self.stdout.write(self.style.WARNING('Run without --dry-run to apply changes'))
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f'✓ COMPLETED: Fixed {total_links_fixed} links in {total_objects_fixed} objects'
                )
            )
        self.stdout.write('=' * 70)

    def fix_model_links(self, model, dry_run=False):
        """Fix links in all English fields for a given model"""
        # Get translatable fields that end with _en
        english_fields = [
            field.name for field in model._meta.get_fields()
            if field.name.endswith('_en') and hasattr(model, field.name)
        ]

        if not english_fields:
            self.stdout.write(
                self.style.WARNING(f'  No English fields found for {model.__name__}')
            )
            return 0, 0

        queryset = model.objects.all()
        objects_fixed = 0
        total_links_fixed = 0

        for obj in queryset:
            updated_fields = {}
            has_changes = False
            object_links_fixed = 0

            for field_name in english_fields:
                original_content = getattr(obj, field_name, '')

                if not original_content or '<a' not in original_content.lower():
                    continue

                # Fix links in content
                fixed_content, links_count = self.fix_links_in_content(original_content)

                if fixed_content != original_content:
                    updated_fields[field_name] = fixed_content
                    has_changes = True
                    object_links_fixed += links_count

                    if dry_run:
                        self.stdout.write(
                            self.style.WARNING(
                                f'  Would fix {model.__name__} #{obj.pk} '
                                f'({getattr(obj, "name", getattr(obj, "title_en", ""))[:50]})'
                            )
                        )
                        self.stdout.write(f'    Field: {field_name}, Links fixed: {links_count}')
                        # Show first link change as example
                        self.show_example_change(original_content, fixed_content)

            if has_changes:
                objects_fixed += 1
                total_links_fixed += object_links_fixed

                if not dry_run:
                    # CRITICAL: Use .update() instead of .save() to bypass Django signals
                    # This prevents triggering translation signals which would cause re-translation

                    # Calculate new hash after fixing links
                    # We need to update the hash so it matches the new content
                    for field_name, value in updated_fields.items():
                        setattr(obj, field_name, value)
                    new_hash = obj.get_translatable_content_hash()
                    updated_fields['translation_source_hash'] = new_hash

                    # Use QuerySet.update() to bypass pre_save/post_save signals
                    with transaction.atomic():
                        model.objects.filter(pk=obj.pk).update(**updated_fields)

                    self.stdout.write(
                        f'  ✓ Fixed {model.__name__} #{obj.pk}: {object_links_fixed} links'
                    )

        return objects_fixed, total_links_fixed

    def fix_links_in_content(self, content):
        """
        Fix internal links by adding /en/ prefix.

        Patterns to fix:
        - href="/strain/..." → href="/en/strain/..."
        - href="/articles/..." → href="/en/articles/..."
        - href="/terpenes/..." → href="/en/terpenes/..."
        - href="/store/..." → href="/en/store/..."

        Does NOT fix:
        - External links (http://, https://)
        - Already fixed links (href="/en/...)
        - Admin/static/media links
        """
        if not content:
            return content, 0

        links_fixed = 0

        # Pattern to match internal links that need fixing
        # Matches href="/ but not /en/, /admin/, /static/, /media/, /i18n/, http://, https://
        # Captures paths starting with: strain, strains, article, articles, terpene, terpenes, store
        pattern = r'href="(/(?!en/|admin/|static/|media/|i18n/|http|https)(strains?|articles?|terpenes?|store)(?:/[^"]*)?)"'

        def add_en_prefix(match):
            """Add /en/ prefix to the captured path"""
            nonlocal links_fixed
            path = match.group(1)
            links_fixed += 1
            return f'href="/en{path}"'

        fixed_content = re.sub(pattern, add_en_prefix, content, flags=re.IGNORECASE)

        return fixed_content, links_fixed

    def show_example_change(self, original, fixed):
        """Show first link change as example"""
        # Find first href difference
        pattern_original = r'href="(/(?!en/|admin/|static/|media/|i18n/|http|https)(strains?|articles?|terpenes?|store)(?:/[^"]*)?)"'
        match_orig = re.search(pattern_original, original, flags=re.IGNORECASE)

        if match_orig:
            old_link = match_orig.group(0)
            new_link = old_link.replace('href="/', 'href="/en/')
            self.stdout.write(f'      Example: {old_link} → {new_link}')
