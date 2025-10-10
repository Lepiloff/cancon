import json
import logging
from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver
from django.conf import settings
from apps.strains.models import Strain, Article, Terpene

logger = logging.getLogger(__name__)


def send_to_translation_queue(model_name, instance_id, fields_to_translate):
    """
    Send translation job to AWS SQS FIFO queue.

    For local development without AWS, this will just log the request.

    Args:
        model_name: Model class name (e.g., 'Strain')
        instance_id: Database ID of the instance
        fields_to_translate: Dict of field names and EN content
    """
    # Check if AWS SQS is configured
    if not settings.AWS_SQS_TRANSLATION_QUEUE_URL:
        logger.info(
            f"[LOCAL DEV] Would send {model_name} #{instance_id} to translation queue. "
            f"Fields: {list(fields_to_translate.keys())}"
        )
        return True

    try:
        import boto3

        sqs = boto3.client('sqs', region_name=settings.AWS_REGION)

        message_body = {
            'model': model_name,
            'instance_id': instance_id,
            'fields': fields_to_translate,
            'source_lang': 'en',
            'target_lang': 'es',
        }

        # Send to FIFO queue
        response = sqs.send_message(
            QueueUrl=settings.AWS_SQS_TRANSLATION_QUEUE_URL,
            MessageBody=json.dumps(message_body),
            MessageGroupId=f'{model_name}-translations',  # Groups messages by model
            MessageDeduplicationId=f'{model_name}-{instance_id}-{fields_to_translate.get("content_hash", "")}',
        )

        logger.info(
            f"Sent {model_name} #{instance_id} to translation queue. "
            f"MessageId: {response['MessageId']}"
        )
        return True

    except Exception as e:
        logger.error(f"Failed to send {model_name} #{instance_id} to queue: {e}")
        return False


# ============================================================================
# STRAIN SIGNALS
# ============================================================================

@receiver(pre_save, sender=Strain)
def check_strain_translation_needed(sender, instance, **kwargs):
    """
    Before saving: Check if English content has changed.
    If changed, mark translation as outdated.
    """
    if not instance.pk:
        # New instance - skip
        return

    try:
        old_instance = sender.objects.get(pk=instance.pk)
        old_hash = old_instance.get_translatable_content_hash()
        new_hash = instance.get_translatable_content_hash()

        if old_hash != new_hash:
            # Content changed - mark as outdated
            instance.translation_status = 'outdated'
            instance.translation_source_hash = None
            logger.info(f"Strain #{instance.pk} marked as outdated due to content change")

    except sender.DoesNotExist:
        pass


@receiver(post_save, sender=Strain)
def queue_strain_translation(sender, instance, created, **kwargs):
    """
    After saving: Queue translation if needed.
    """
    if instance.needs_translation():
        # Get translatable content
        fields = instance.get_translatable_fields()

        if not fields:
            logger.warning(f"Strain #{instance.pk} needs translation but has no EN content")
            return

        # Add content hash for deduplication
        fields['content_hash'] = instance.get_translatable_content_hash()

        # Send to queue
        success = send_to_translation_queue('Strain', instance.id, fields)

        if success:
            # Update status to pending
            Strain.objects.filter(pk=instance.pk).update(translation_status='pending')
            logger.info(f"Strain #{instance.pk} queued for translation")


# ============================================================================
# ARTICLE SIGNALS
# ============================================================================

@receiver(pre_save, sender=Article)
def check_article_translation_needed(sender, instance, **kwargs):
    """Before saving: Check if English content has changed."""
    if not instance.pk:
        return

    try:
        old_instance = sender.objects.get(pk=instance.pk)
        old_hash = old_instance.get_translatable_content_hash()
        new_hash = instance.get_translatable_content_hash()

        if old_hash != new_hash:
            instance.translation_status = 'outdated'
            instance.translation_source_hash = None
            logger.info(f"Article #{instance.pk} marked as outdated")

    except sender.DoesNotExist:
        pass


@receiver(post_save, sender=Article)
def queue_article_translation(sender, instance, created, **kwargs):
    """After saving: Queue translation if needed."""
    if instance.needs_translation():
        fields = instance.get_translatable_fields()

        if not fields:
            logger.warning(f"Article #{instance.pk} needs translation but has no EN content")
            return

        fields['content_hash'] = instance.get_translatable_content_hash()

        success = send_to_translation_queue('Article', instance.id, fields)

        if success:
            Article.objects.filter(pk=instance.pk).update(translation_status='pending')
            logger.info(f"Article #{instance.pk} queued for translation")


# ============================================================================
# TERPENE SIGNALS
# ============================================================================

@receiver(pre_save, sender=Terpene)
def check_terpene_translation_needed(sender, instance, **kwargs):
    """Before saving: Check if English content has changed."""
    if not instance.pk:
        return

    try:
        old_instance = sender.objects.get(pk=instance.pk)
        old_hash = old_instance.get_translatable_content_hash()
        new_hash = instance.get_translatable_content_hash()

        if old_hash != new_hash:
            instance.translation_status = 'outdated'
            instance.translation_source_hash = None
            logger.info(f"Terpene #{instance.pk} marked as outdated")

    except sender.DoesNotExist:
        pass


@receiver(post_save, sender=Terpene)
def queue_terpene_translation(sender, instance, created, **kwargs):
    """After saving: Queue translation if needed."""
    if instance.needs_translation():
        fields = instance.get_translatable_fields()

        if not fields:
            logger.warning(f"Terpene #{instance.pk} needs translation but has no EN content")
            return

        fields['content_hash'] = instance.get_translatable_content_hash()

        success = send_to_translation_queue('Terpene', instance.id, fields)

        if success:
            Terpene.objects.filter(pk=instance.pk).update(translation_status='pending')
            logger.info(f"Terpene #{instance.pk} queued for translation")
