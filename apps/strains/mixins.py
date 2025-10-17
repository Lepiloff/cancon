import hashlib
import json
from django.db import models
from django.utils import timezone


class TranslationMixin(models.Model):
    """
    Mixin for tracking translation synchronization between EN (source) and ES (target).
    Uses SHA256 hash to detect content changes.
    """

    # Hash of source content (EN) at the time of last translation
    translation_source_hash = models.CharField(
        max_length=64,
        blank=True,
        null=True,
        help_text="SHA256 hash of English content when last translated"
    )

    # Translation status
    TRANSLATION_STATUS_CHOICES = [
        ('synced', 'Synced'),
        ('pending', 'Pending'),
        ('outdated', 'Outdated'),
        ('failed', 'Failed'),
    ]
    translation_status = models.CharField(
        max_length=20,
        choices=TRANSLATION_STATUS_CHOICES,
        default='pending',
        db_index=True
    )

    # Metadata
    last_translated_at = models.DateTimeField(
        blank=True,
        null=True,
        help_text="Timestamp of last successful translation"
    )
    translation_error = models.TextField(
        blank=True,
        null=True,
        help_text="Error message if translation failed"
    )

    class Meta:
        abstract = True

    def get_translatable_fields(self):
        """
        Returns dict of translatable fields in English.
        Override this method in child classes if needed.
        """
        fields = {}

        # Check which fields exist on the model
        translatable_field_names = ['name', 'description', 'title', 'text_content', 'keywords']

        for field_name in translatable_field_names:
            en_field = f'{field_name}_en'
            if hasattr(self, en_field):
                value = getattr(self, en_field, '')
                if value:  # Only include non-empty fields
                    fields[field_name] = value

        return fields

    def get_translatable_content_hash(self):
        """
        Generates SHA256 hash for all translatable English fields.
        Used to detect content changes.

        IMPORTANT: Strips HTML tags and normalizes whitespace before hashing.
        This means changes to HTML formatting (e.g., <h1> to <h2>) won't trigger re-translation.
        Only actual text content changes will trigger translation.
        """
        from django.utils.html import strip_tags
        import re

        content = self.get_translatable_fields()

        # Normalize content: strip HTML tags and collapse whitespace
        normalized = {}
        for key, value in content.items():
            if value:
                # Strip HTML tags
                clean_text = strip_tags(str(value))
                # Normalize whitespace (collapse multiple spaces/newlines to single space)
                clean_text = re.sub(r'\s+', ' ', clean_text).strip()
                normalized[key] = clean_text
            else:
                normalized[key] = ''

        # Sort keys for hash stability
        content_str = json.dumps(normalized, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(content_str.encode('utf-8')).hexdigest()

    def needs_translation(self):
        """
        Determines if this instance needs translation.

        Returns True if:
        1. Spanish translation doesn't exist
        2. English content has changed since last translation
        3. Previous translation failed
        """
        # Case 1: No Spanish translation exists
        # Check if any _es field is empty
        has_es_translation = False
        for field_name in ['name', 'description', 'title', 'text_content']:
            es_field = f'{field_name}_es'
            if hasattr(self, es_field):
                if getattr(self, es_field, None):
                    has_es_translation = True
                    break

        if not has_es_translation:
            return True

        # Case 2: Content has changed since last translation
        current_hash = self.get_translatable_content_hash()
        if self.translation_source_hash != current_hash:
            return True

        # Case 3: Previous translation failed
        if self.translation_status == 'failed':
            return True

        return False

    def mark_translation_pending(self):
        """Mark this instance as pending translation"""
        self.translation_status = 'pending'
        self.save(update_fields=['translation_status'])

    def mark_translation_synced(self, source_hash=None):
        """Mark this instance as successfully translated"""
        self.translation_status = 'synced'
        self.translation_source_hash = source_hash or self.get_translatable_content_hash()
        self.last_translated_at = timezone.now()
        self.translation_error = None
        self.save(update_fields=[
            'translation_status',
            'translation_source_hash',
            'last_translated_at',
            'translation_error'
        ])

    def mark_translation_failed(self, error_message):
        """Mark this instance as failed translation with error message"""
        self.translation_status = 'failed'
        self.translation_error = error_message[:1000]  # Limit error message length
        self.save(update_fields=['translation_status', 'translation_error'])
