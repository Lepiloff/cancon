from unittest import mock

from allauth.account.models import EmailAddress
from django.contrib.auth import get_user_model
from django.core import mail
from django.test import Client, TestCase, override_settings
from django.urls import reverse


User = get_user_model()


@override_settings(
    EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
    CELERY_TASK_ALWAYS_EAGER=True,
    CELERY_TASK_EAGER_PROPAGATES=True,
    ACCOUNT_EMAIL_VERIFICATION='mandatory',
)
class AccountAdapterTests(TestCase):
    def test_send_mail_enqueues_celery_task(self):
        from users.adapters import AccountAdapter

        adapter = AccountAdapter()
        with mock.patch('users.adapters.send_email_task.delay') as enqueue:
            adapter.send_mail(
                'account/email/email_confirmation',
                'recipient@example.com',
                {
                    'user': User(email='recipient@example.com'),
                    'activate_url': 'https://example.com/activate/abc',
                    'current_site': mock.Mock(name='example', domain='example.com'),
                    'key': 'abc',
                },
            )

        self.assertEqual(enqueue.call_count, 1)
        kwargs = enqueue.call_args.kwargs
        self.assertEqual(kwargs['recipients'], ['recipient@example.com'])
        self.assertIn('Cannamente', kwargs['subject'])
        self.assertTrue(kwargs['body'])

    def test_celery_task_actually_sends_email(self):
        """In eager mode, calling send_mail should result in a real outgoing email."""
        from users.adapters import AccountAdapter

        adapter = AccountAdapter()
        adapter.send_mail(
            'account/email/email_confirmation',
            'recipient@example.com',
            {
                'user': User(email='recipient@example.com'),
                'activate_url': 'https://example.com/activate/abc',
                'current_site': mock.Mock(name='example', domain='example.com'),
                'key': 'abc',
                'code': '123456',
            },
        )

        self.assertEqual(len(mail.outbox), 1)
        sent = mail.outbox[0]
        self.assertEqual(sent.to, ['recipient@example.com'])
        self.assertIn('123456', sent.body)


@override_settings(
    EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
    CELERY_TASK_ALWAYS_EAGER=True,
    CELERY_TASK_EAGER_PROPAGATES=True,
    ACCOUNT_EMAIL_VERIFICATION='mandatory',
)
class SignupVerificationFlowTests(TestCase):
    def test_signup_creates_unverified_email_and_sends_confirmation(self):
        client = Client()
        response = client.post(
            reverse('account_signup'),
            data={
                'email': 'newuser@example.com',
                'password1': 'StrongPass!2345',
                'password2': 'StrongPass!2345',
            },
        )

        self.assertIn(response.status_code, (200, 302))
        user = User.objects.get(email='newuser@example.com')
        email_address = EmailAddress.objects.get(user=user, email__iexact='newuser@example.com')
        self.assertFalse(email_address.verified)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ['newuser@example.com'])

    def test_password_reset_sends_email_for_existing_user(self):
        user = User.objects.create_user(email='member@example.com', password='OldPass!1234')
        EmailAddress.objects.create(user=user, email=user.email, verified=True, primary=True)

        client = Client()
        response = client.post(
            reverse('account_reset_password'),
            data={'email': 'member@example.com'},
        )

        self.assertIn(response.status_code, (200, 302))
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('member@example.com', mail.outbox[0].to)
