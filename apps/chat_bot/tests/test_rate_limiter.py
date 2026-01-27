"""
Tests for chat rate limiter functionality.
"""

from datetime import timedelta
from unittest.mock import patch

from django.test import TestCase, override_settings
from django.utils import timezone

from apps.chat_bot.models import ChatRateLimit
from apps.chat_bot.rate_limiter import (
    check_rate_limit,
    RateLimitExceeded,
    format_retry_after_human,
    get_rate_limit_settings,
)


@override_settings(CHAT_RATE_LIMIT_MAX_REQUESTS=5, CHAT_RATE_LIMIT_WINDOW_SECONDS=3600)
class RateLimiterTestCase(TestCase):
    """Tests for rate limiting logic"""

    def setUp(self):
        self.test_ip = '192.168.1.100'

    def test_first_request_creates_record(self):
        """First request should create a new rate limit record"""
        self.assertEqual(ChatRateLimit.objects.count(), 0)

        result = check_rate_limit(self.test_ip)

        self.assertTrue(result)
        self.assertEqual(ChatRateLimit.objects.count(), 1)

        record = ChatRateLimit.objects.get(ip_address=self.test_ip)
        self.assertEqual(record.request_count, 1)

    def test_subsequent_requests_increment_counter(self):
        """Subsequent requests should increment the counter"""
        check_rate_limit(self.test_ip)
        check_rate_limit(self.test_ip)
        check_rate_limit(self.test_ip)

        record = ChatRateLimit.objects.get(ip_address=self.test_ip)
        self.assertEqual(record.request_count, 3)

    def test_rate_limit_exceeded_raises_exception(self):
        """Should raise RateLimitExceeded when limit is reached"""
        # Make 5 requests (the limit)
        for _ in range(5):
            check_rate_limit(self.test_ip)

        # 6th request should fail
        with self.assertRaises(RateLimitExceeded) as context:
            check_rate_limit(self.test_ip)

        self.assertGreater(context.exception.retry_after_seconds, 0)
        self.assertLessEqual(context.exception.retry_after_seconds, 3600)

    def test_rate_limit_exceeded_updates_last_exceeded_at(self):
        """Should update last_exceeded_at when limit is exceeded"""
        for _ in range(5):
            check_rate_limit(self.test_ip)

        with self.assertRaises(RateLimitExceeded):
            check_rate_limit(self.test_ip)

        record = ChatRateLimit.objects.get(ip_address=self.test_ip)
        self.assertIsNotNone(record.last_exceeded_at)

    def test_expired_window_resets_counter(self):
        """Counter should reset when window expires"""
        # Create initial record
        check_rate_limit(self.test_ip)
        check_rate_limit(self.test_ip)

        # Manually set window_start to the past (expired)
        record = ChatRateLimit.objects.get(ip_address=self.test_ip)
        record.window_start = timezone.now() - timedelta(hours=2)
        record.save()

        # Next request should reset counter
        check_rate_limit(self.test_ip)

        record.refresh_from_db()
        self.assertEqual(record.request_count, 1)

    def test_different_ips_have_separate_limits(self):
        """Each IP should have its own rate limit"""
        ip1 = '192.168.1.1'
        ip2 = '192.168.1.2'

        # Make requests from both IPs
        for _ in range(3):
            check_rate_limit(ip1)
        for _ in range(2):
            check_rate_limit(ip2)

        record1 = ChatRateLimit.objects.get(ip_address=ip1)
        record2 = ChatRateLimit.objects.get(ip_address=ip2)

        self.assertEqual(record1.request_count, 3)
        self.assertEqual(record2.request_count, 2)

    def test_retry_after_calculation(self):
        """retry_after_seconds should be time until window expires"""
        # Create record with known window_start
        check_rate_limit(self.test_ip)

        record = ChatRateLimit.objects.get(ip_address=self.test_ip)
        # Set window_start to 30 minutes ago
        record.window_start = timezone.now() - timedelta(minutes=30)
        record.request_count = 5  # At the limit
        record.save()

        with self.assertRaises(RateLimitExceeded) as context:
            check_rate_limit(self.test_ip)

        # Should be approximately 30 minutes (1800 seconds)
        self.assertGreater(context.exception.retry_after_seconds, 1700)
        self.assertLessEqual(context.exception.retry_after_seconds, 1900)


class FormatRetryAfterHumanTestCase(TestCase):
    """Tests for human-readable retry_after formatting"""

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
    """Tests for settings retrieval"""

    @override_settings(CHAT_RATE_LIMIT_MAX_REQUESTS=20, CHAT_RATE_LIMIT_WINDOW_SECONDS=7200)
    def test_custom_settings(self):
        max_requests, window_seconds = get_rate_limit_settings()
        self.assertEqual(max_requests, 20)
        self.assertEqual(window_seconds, 7200)

    def test_default_settings(self):
        """When settings are not defined, should use defaults"""
        # Delete settings if they exist
        with override_settings():
            # Remove the settings by not setting them
            from django.conf import settings
            if hasattr(settings, 'CHAT_RATE_LIMIT_MAX_REQUESTS'):
                delattr(settings, 'CHAT_RATE_LIMIT_MAX_REQUESTS')
            if hasattr(settings, 'CHAT_RATE_LIMIT_WINDOW_SECONDS'):
                delattr(settings, 'CHAT_RATE_LIMIT_WINDOW_SECONDS')

            max_requests, window_seconds = get_rate_limit_settings()
            self.assertEqual(max_requests, 10)  # Default
            self.assertEqual(window_seconds, 3600)  # Default
