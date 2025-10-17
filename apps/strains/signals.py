"""
Translation Signals

Automatically translate content when saved in admin.
Phase 3: Synchronous translation using OpenAI API (no SQS/Lambda).
"""

import logging
import os
from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver
from django.conf import settings

from apps.strains.models import Strain, Article, Terpene
from apps.translation import OpenAITranslator, TranslationConfig
from apps.translation.base_translator import TranslationError

logger = logging.getLogger(__name__)


# Check if translations are enabled (can be disabled for testing)
# Auto-disable if OPENAI_API_KEY is not set (e.g., in CI/CD tests)
ENABLE_AUTO_TRANSLATION = getattr(
    settings,
    'ENABLE_AUTO_TRANSLATION',
    bool(os.getenv('OPENAI_API_KEY'))  # Only enable if API key exists
)

# Translation direction (en-to-es or es-to-en)
TRANSLATION_DIRECTION = getattr(
    settings,
    'TRANSLATION_DIRECTION',
    'en-to-es'  # Default: English to Spanish
)


def perform_translation(instance, model_name: str) -> bool:
    """
    Perform translation for an instance.

    Args:
        instance: Model instance to translate
        model_name: Model name (Strain, Article, Terpene)

    Returns:
        True if translation succeeded, False otherwise
    """
    if not ENABLE_AUTO_TRANSLATION:
        logger.info(f'Auto-translation disabled, skipping {model_name} #{instance.id}')
        return False

    # Double-check API key exists before attempting translation
    if not os.getenv('OPENAI_API_KEY'):
        logger.warning(
            f'OPENAI_API_KEY not set, skipping translation for {model_name} #{instance.id}'
        )
        return False

    try:
        # Parse translation direction
        source_lang, target_lang = TranslationConfig.parse_direction(
            TRANSLATION_DIRECTION
        )

        # Get fields to translate
        fields_to_translate = {}
        field_names = TranslationConfig.get_model_fields(model_name)

        for field_name in field_names:
            source_field = f'{field_name}_{source_lang}'
            if hasattr(instance, source_field):
                content = getattr(instance, source_field, '')
                if content:
                    fields_to_translate[field_name] = content

        if not fields_to_translate:
            logger.info(
                f'No source content to translate for {model_name} #{instance.id}'
            )
            return False

        logger.info(
            f'Translating {model_name} #{instance.id} ({source_lang} → {target_lang})'
        )

        # Initialize translator and translate
        translator = OpenAITranslator()
        translations = translator.translate(
            model_name,
            fields_to_translate,
            source_lang,
            target_lang,
        )

        # Save translations
        translated_fields = []
        for field_name, translated_text in translations.items():
            target_field = f'{field_name}_{target_lang}'
            if hasattr(instance, target_field):
                setattr(instance, target_field, translated_text)
                translated_fields.append(target_field)

        # Update translation metadata
        from django.utils import timezone
        instance.translation_status = 'synced'
        instance.translation_source_hash = instance.get_translatable_content_hash()
        instance.last_translated_at = timezone.now()
        instance.translation_error = None

        # Save everything at once with update_fields to avoid triggering signals again
        update_fields = translated_fields + [
            'translation_status',
            'translation_source_hash',
            'last_translated_at',
            'translation_error'
        ]
        instance.save(update_fields=update_fields)

        logger.info(
            f'Successfully translated {model_name} #{instance.id} '
            f'({len(translations)} fields)'
        )

        return True

    except TranslationError as e:
        error_msg = f'Translation failed: {str(e)}'
        logger.error(f'{model_name} #{instance.id}: {error_msg}')
        instance.mark_translation_failed(error_msg)
        return False

    except Exception as e:
        error_msg = f'Unexpected error during translation: {str(e)}'
        logger.exception(f'{model_name} #{instance.id}: {error_msg}')
        instance.mark_translation_failed(error_msg)
        return False


# ========== Strain Signals ==========

@receiver(pre_save, sender=Strain)
def check_strain_translation_needed(sender, instance, **kwargs):
    """
    Check if strain content has changed and mark as outdated if needed.

    This runs before save to detect content changes.
    """
    if not instance.pk:
        # New object, will be handled in post_save
        return

    try:
        old_instance = sender.objects.get(pk=instance.pk)
        old_hash = old_instance.get_translatable_content_hash()
        new_hash = instance.get_translatable_content_hash()

        if old_hash != new_hash:
            # Content changed, mark as outdated
            instance.translation_status = 'outdated'
            logger.info(
                f'Strain #{instance.id} content changed, marking as outdated'
            )
    except sender.DoesNotExist:
        pass


@receiver(post_save, sender=Strain)
def auto_translate_strain(sender, instance, created, **kwargs):
    """
    Automatically translate strain after save if needed.

    This runs after save to perform translation.
    """
    # Skip if translations are disabled
    if not ENABLE_AUTO_TRANSLATION:
        return

    # Check if translation is needed
    if not instance.needs_translation():
        logger.debug(f'Strain #{instance.id} does not need translation')
        return

    # Perform translation
    logger.info(f'Auto-translating Strain #{instance.id}')
    perform_translation(instance, 'Strain')


# ========== Article Signals ==========

@receiver(pre_save, sender=Article)
def check_article_translation_needed(sender, instance, **kwargs):
    """
    Check if article content has changed and mark as outdated if needed.
    """
    if not instance.pk:
        return

    try:
        old_instance = sender.objects.get(pk=instance.pk)
        old_hash = old_instance.get_translatable_content_hash()
        new_hash = instance.get_translatable_content_hash()

        if old_hash != new_hash:
            instance.translation_status = 'outdated'
            logger.info(
                f'Article #{instance.id} content changed, marking as outdated'
            )
    except sender.DoesNotExist:
        pass


@receiver(post_save, sender=Article)
def auto_translate_article(sender, instance, created, **kwargs):
    """
    Automatically translate article after save if needed.
    """
    if not ENABLE_AUTO_TRANSLATION:
        return

    if not instance.needs_translation():
        logger.debug(f'Article #{instance.id} does not need translation')
        return

    logger.info(f'Auto-translating Article #{instance.id}')
    perform_translation(instance, 'Article')


# ========== Terpene Signals ==========

@receiver(pre_save, sender=Terpene)
def check_terpene_translation_needed(sender, instance, **kwargs):
    """
    Check if terpene content has changed and mark as outdated if needed.
    """
    if not instance.pk:
        return

    try:
        old_instance = sender.objects.get(pk=instance.pk)
        old_hash = old_instance.get_translatable_content_hash()
        new_hash = instance.get_translatable_content_hash()

        if old_hash != new_hash:
            instance.translation_status = 'outdated'
            logger.info(
                f'Terpene #{instance.id} content changed, marking as outdated'
            )
    except sender.DoesNotExist:
        pass


@receiver(post_save, sender=Terpene)
def auto_translate_terpene(sender, instance, created, **kwargs):
    """
    Automatically translate terpene after save if needed.
    """
    if not ENABLE_AUTO_TRANSLATION:
        return

    if not instance.needs_translation():
        logger.debug(f'Terpene #{instance.id} does not need translation')
        return

    logger.info(f'Auto-translating Terpene #{instance.id}')
    perform_translation(instance, 'Terpene')
