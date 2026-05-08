from celery import shared_task
from celery.utils.log import get_task_logger
from django.core.mail import EmailMultiAlternatives


logger = get_task_logger(__name__)


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=600,
    retry_jitter=True,
    max_retries=5,
)
def send_email_task(self, subject, body, from_email, recipients, html_body=None, headers=None):
    """Send a transactional email through the configured EMAIL_BACKEND.

    Retries on any exception with exponential backoff.
    """
    message = EmailMultiAlternatives(
        subject=subject,
        body=body,
        from_email=from_email,
        to=recipients,
        headers=headers or None,
    )
    if html_body:
        message.attach_alternative(html_body, 'text/html')

    sent = message.send()
    logger.info('Email sent to %s (subject=%r, sent=%s)', recipients, subject, sent)
    return sent
