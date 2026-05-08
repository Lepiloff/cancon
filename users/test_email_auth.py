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

    def test_signup_then_confirm_with_code_logs_user_in(self):
        """Full flow: signup → grab code from session → submit → email verified."""
        client = Client()
        client.post(
            reverse('account_signup'),
            data={
                'email': 'flow@example.com',
                'password1': 'StrongPass!2345',
                'password2': 'StrongPass!2345',
            },
        )

        verification = client.session.get('account_email_verification_code')
        self.assertIsNotNone(verification, 'allauth should have stashed a code in session')
        code = verification['code']
        self.assertEqual(len(code), 6)

        confirm_response = client.post(
            reverse('account_email_verification_sent'),
            data={'code': code},
            follow=True,
        )

        self.assertEqual(confirm_response.status_code, 200)
        email_address = EmailAddress.objects.get(email__iexact='flow@example.com')
        self.assertTrue(email_address.verified)
        self.assertTrue(
            client.session.get('_auth_user_id'),
            'user should be logged in after successful code confirmation',
        )

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


class BackfillMigrationTests(TestCase):
    """Direct exercise of the migration's backfill helper.

    pytest.ini sets --nomigrations so the migration itself does not run during
    tests; we test the helper against the live models, which share the same
    invariants as the historical models the migration uses.
    """

    def _backfill(self):
        import importlib

        mod = importlib.import_module(
            'users.migrations.0005_mark_existing_emails_verified',
        )
        mod.backfill_email_addresses(User, EmailAddress)

    def test_user_with_no_email_address_gets_one_created(self):
        user = User.objects.create_user(email='fresh@example.com', password='Pass!12345')
        EmailAddress.objects.filter(user=user).delete()

        self._backfill()

        ea = EmailAddress.objects.get(user=user, email__iexact='fresh@example.com')
        self.assertTrue(ea.verified)
        self.assertTrue(ea.primary)

    def test_existing_unverified_row_gets_verified_without_touching_primary(self):
        user = User.objects.create_user(email='dup@example.com', password='Pass!12345')
        EmailAddress.objects.filter(user=user).delete()
        # Pre-existing scenario: another email is already primary, ours is not.
        other_primary = EmailAddress.objects.create(
            user=user, email='other@example.com', verified=False, primary=True,
        )
        ours = EmailAddress.objects.create(
            user=user, email='dup@example.com', verified=False, primary=False,
        )

        self._backfill()

        ours.refresh_from_db()
        other_primary.refresh_from_db()
        self.assertTrue(ours.verified, 'matching row must end up verified')
        self.assertFalse(ours.primary, 'must not flip primary on existing row')
        self.assertTrue(other_primary.primary, 'must not unset existing primary')

    def test_user_with_existing_primary_unrelated_email_does_not_violate_unique(self):
        """The risky case: row matching User.email is missing, but another primary exists."""
        user = User.objects.create_user(email='solo@example.com', password='Pass!12345')
        EmailAddress.objects.filter(user=user).delete()
        EmailAddress.objects.create(
            user=user, email='legacy@example.com', verified=True, primary=True,
        )

        self._backfill()

        new_row = EmailAddress.objects.get(user=user, email__iexact='solo@example.com')
        self.assertTrue(new_row.verified)
        self.assertFalse(new_row.primary, 'new row must not duplicate existing primary')
        self.assertEqual(EmailAddress.objects.filter(user=user, primary=True).count(), 1)
