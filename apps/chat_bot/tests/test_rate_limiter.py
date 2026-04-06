"""
Tests for chat rate limiter functionality.
"""

from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.utils import timezone

from apps.chat_bot.models import ChatRateLimit, ChatRateLimitUser
from apps.chat_bot.rate_limiter import (
    RateLimitExceeded,
    check_rate_limit,
    format_retry_after_human,
    get_rate_limit_settings,
)


User = get_user_model()


@override_settings(
    CHAT_RATE_LIMIT_ANON_MAX_REQUESTS=5,
    CHAT_RATE_LIMIT_AUTH_MAX_REQUESTS=10,
    CHAT_RATE_LIMIT_WINDOW_SECONDS=3600,
)
class RateLimiterTestCase(TestCase):
    """Tests for rate limiting logic."""

    def setUp(self):
        self.test_ip = '192.168.1.100'
        self.user = User.objects.create_user(
            email='rate-limit@example.com',
            password='testpass123',
        )

    def test_first_request_creates_ip_record(self):
        self.assertEqual(ChatRateLimit.objects.count(), 0)

        result = check_rate_limit(self.test_ip)

        self.assertTrue(result)
        self.assertEqual(ChatRateLimit.objects.count(), 1)
        self.assertEqual(ChatRateLimit.objects.get(ip_address=self.test_ip).request_count, 1)

    def test_authenticated_first_request_creates_user_record(self):
        self.assertEqual(ChatRateLimitUser.objects.count(), 0)

        result = check_rate_limit(self.test_ip, self.user)

        self.assertTrue(result)
        self.assertEqual(ChatRateLimitUser.objects.count(), 1)
        self.assertEqual(ChatRateLimitUser.objects.get(user=self.user).request_count, 1)
        self.assertFalse(ChatRateLimit.objects.filter(ip_address=self.test_ip).exists())

    def test_anonymous_limit_is_5(self):
        for _ in range(5):
            check_rate_limit(self.test_ip)

        with self.assertRaises(RateLimitExceeded):
            check_rate_limit(self.test_ip)

    def test_authenticated_limit_is_10(self):
        for _ in range(10):
            check_rate_limit(self.test_ip, self.user)

        with self.assertRaises(RateLimitExceeded):
            check_rate_limit(self.test_ip, self.user)

    def test_authenticated_requests_do_not_consume_ip_bucket(self):
        for _ in range(3):
            check_rate_limit(self.test_ip, self.user)

        self.assertFalse(ChatRateLimit.objects.filter(ip_address=self.test_ip).exists())
        self.assertEqual(ChatRateLimitUser.objects.get(user=self.user).request_count, 3)

    def test_backward_compat_without_user_param_uses_anonymous_settings(self):
        check_rate_limit(self.test_ip)
        self.assertEqual(ChatRateLimit.objects.get(ip_address=self.test_ip).request_count, 1)

    def test_subsequent_requests_increment_counter(self):
        check_rate_limit(self.test_ip)
        check_rate_limit(self.test_ip)
        check_rate_limit(self.test_ip)

        record = ChatRateLimit.objects.get(ip_address=self.test_ip)
        self.assertEqual(record.request_count, 3)

    def test_different_ips_have_separate_limits(self):
        ip1 = '192.168.1.1'
        ip2 = '192.168.1.2'

        for _ in range(3):
            check_rate_limit(ip1)
        for _ in range(2):
            check_rate_limit(ip2)

        self.assertEqual(ChatRateLimit.objects.get(ip_address=ip1).request_count, 3)
        self.assertEqual(ChatRateLimit.objects.get(ip_address=ip2).request_count, 2)

    def test_different_users_have_separate_limits(self):
        other_user = User.objects.create_user(
            email='other-rate-limit@example.com',
            password='testpass123',
        )

        for _ in range(4):
            check_rate_limit(self.test_ip, self.user)
        for _ in range(2):
            check_rate_limit(self.test_ip, other_user)

        self.assertEqual(ChatRateLimitUser.objects.get(user=self.user).request_count, 4)
        self.assertEqual(ChatRateLimitUser.objects.get(user=other_user).request_count, 2)

    def test_rate_limit_exceeded_updates_last_exceeded_at(self):
        for _ in range(5):
            check_rate_limit(self.test_ip)

        with self.assertRaises(RateLimitExceeded):
            check_rate_limit(self.test_ip)

        self.assertIsNotNone(ChatRateLimit.objects.get(ip_address=self.test_ip).last_exceeded_at)

    def test_expired_ip_window_resets_counter(self):
        check_rate_limit(self.test_ip)
        check_rate_limit(self.test_ip)

        record = ChatRateLimit.objects.get(ip_address=self.test_ip)
        record.window_start = timezone.now() - timedelta(hours=2)
        record.save()

        check_rate_limit(self.test_ip)

        record.refresh_from_db()
        self.assertEqual(record.request_count, 1)
        self.assertIsNone(record.last_exceeded_at)

    def test_expired_user_window_resets_counter(self):
        check_rate_limit(self.test_ip, self.user)
        check_rate_limit(self.test_ip, self.user)

        record = ChatRateLimitUser.objects.get(user=self.user)
        record.window_start = timezone.now() - timedelta(hours=2)
        record.last_exceeded_at = timezone.now() - timedelta(minutes=5)
        record.save()

        check_rate_limit(self.test_ip, self.user)

        record.refresh_from_db()
        self.assertEqual(record.request_count, 1)
        self.assertIsNone(record.last_exceeded_at)

    def test_retry_after_calculation(self):
        check_rate_limit(self.test_ip)

        record = ChatRateLimit.objects.get(ip_address=self.test_ip)
        record.window_start = timezone.now() - timedelta(minutes=30)
        record.request_count = 5
        record.save()

        with self.assertRaises(RateLimitExceeded) as context:
            check_rate_limit(self.test_ip)

        self.assertGreater(context.exception.retry_after_seconds, 1700)
        self.assertLessEqual(context.exception.retry_after_seconds, 1900)


class FormatRetryAfterHumanTestCase(TestCase):
    """Tests for human-readable retry_after formatting."""

    def test_format_seconds_english(self):
        self.assertEqual(format_retry_after_human(1), '1 second')
        self.assertEqual(format_retry_after_human(30), '30 seconds')
        self.assertEqual(format_retry_after_human(59), '59 seconds')

    def test_format_minutes_english(self):
        self.assertEqual(format_retry_after_human(60), '1 minute')
        self.assertEqual(format_retry_after_human(120), '2 minutes')
        self.assertEqual(format_retry_after_human(300), '5 minutes')
        self.assertEqual(format_retry_after_human(3599), '59 minutes')

    def test_format_hours_english(self):
        self.assertEqual(format_retry_after_human(3600), '1 hour')
        self.assertEqual(format_retry_after_human(7200), '2 hours')

    def test_format_hours_and_minutes_english(self):
        self.assertEqual(format_retry_after_human(3660), '1 hour and 1 minute')
        self.assertEqual(format_retry_after_human(7320), '2 hours and 2 minutes')

    def test_format_seconds_spanish(self):
        self.assertEqual(format_retry_after_human(1, 'es'), '1 segundo')
        self.assertEqual(format_retry_after_human(30, 'es'), '30 segundos')

    def test_format_minutes_spanish(self):
        self.assertEqual(format_retry_after_human(60, 'es'), '1 minuto')
        self.assertEqual(format_retry_after_human(120, 'es'), '2 minutos')

    def test_format_hours_spanish(self):
        self.assertEqual(format_retry_after_human(3600, 'es'), '1 hora')
        self.assertEqual(format_retry_after_human(7200, 'es'), '2 horas')

    def test_format_hours_and_minutes_spanish(self):
        self.assertEqual(format_retry_after_human(3660, 'es'), '1 hora y 1 minuto')
        self.assertEqual(format_retry_after_human(7320, 'es'), '2 horas y 2 minutos')


class GetRateLimitSettingsTestCase(TestCase):
    """Tests for settings retrieval."""

    def setUp(self):
        self.user = User.objects.create_user(
            email='settings@example.com',
            password='testpass123',
        )

    @override_settings(
        CHAT_RATE_LIMIT_ANON_MAX_REQUESTS=5,
        CHAT_RATE_LIMIT_AUTH_MAX_REQUESTS=12,
        CHAT_RATE_LIMIT_WINDOW_SECONDS=7200,
    )
    def test_custom_settings_for_anonymous_and_authenticated_users(self):
        anon_max, anon_window = get_rate_limit_settings()
        auth_max, auth_window = get_rate_limit_settings(self.user)

        self.assertEqual(anon_max, 5)
        self.assertEqual(auth_max, 12)
        self.assertEqual(anon_window, 7200)
        self.assertEqual(auth_window, 7200)

    def test_default_settings(self):
        with override_settings():
            from django.conf import settings

            for attr in (
                'CHAT_RATE_LIMIT_MAX_REQUESTS',
                'CHAT_RATE_LIMIT_ANON_MAX_REQUESTS',
                'CHAT_RATE_LIMIT_AUTH_MAX_REQUESTS',
                'CHAT_RATE_LIMIT_WINDOW_SECONDS',
            ):
                if hasattr(settings, attr):
                    delattr(settings, attr)

            anon_max, anon_window = get_rate_limit_settings()
            auth_max, auth_window = get_rate_limit_settings(self.user)

            self.assertEqual(anon_max, 10)
            self.assertEqual(auth_max, 10)
            self.assertEqual(anon_window, 3600)
            self.assertEqual(auth_window, 3600)
