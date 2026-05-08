from allauth.account.adapter import DefaultAccountAdapter

from .tasks import send_email_task


class AccountAdapter(DefaultAccountAdapter):
    """Allauth adapter that dispatches email sending to a Celery worker."""

    def send_mail(self, template_prefix, email, context):
        message = self.render_mail(template_prefix, email, context)
        html_body = None
        for content, mimetype in getattr(message, 'alternatives', []):
            if mimetype == 'text/html':
                html_body = content
                break

        send_email_task.delay(
            subject=message.subject,
            body=message.body,
            from_email=message.from_email,
            recipients=list(message.to),
            html_body=html_body,
            headers=dict(message.extra_headers) if message.extra_headers else None,
        )
