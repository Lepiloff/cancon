"""
Rate limiting logic for chat endpoint.

Uses PostgreSQL for storage with atomic counters and row-level locking.
"""

from django.conf import settings
from django.db import IntegrityError, transaction
from django.utils import timezone
from datetime import timedelta


class RateLimitExceeded(Exception):
    """Raised when rate limit is exceeded"""

    def __init__(self, retry_after_seconds: int, message: str = "Rate limit exceeded"):
        self.retry_after_seconds = retry_after_seconds
        self.message = message
        super().__init__(self.message)


def get_rate_limit_settings(user=None):
    """Get rate limit configuration from settings."""
    legacy_default = getattr(settings, 'CHAT_RATE_LIMIT_MAX_REQUESTS', 10)
    anon_requests = getattr(settings, 'CHAT_RATE_LIMIT_ANON_MAX_REQUESTS', legacy_default)
    auth_requests = getattr(settings, 'CHAT_RATE_LIMIT_AUTH_MAX_REQUESTS', legacy_default)
    window_seconds = getattr(settings, 'CHAT_RATE_LIMIT_WINDOW_SECONDS', 3600)
    if user is not None and getattr(user, 'is_authenticated', False):
        return auth_requests, window_seconds
    return anon_requests, window_seconds


def _get_or_create_locked_record(model, now, **lookup):
    """Fetch a rate-limit row with a lock, tolerating first-write races."""
    try:
        return model.objects.select_for_update().get(**lookup)
    except model.DoesNotExist:
        try:
            return model.objects.create(window_start=now, **lookup)
        except IntegrityError:
            return model.objects.select_for_update().get(**lookup)


def _check_rate_limit_record(model, now, max_requests, window_seconds, **lookup) -> bool:
    """Check and increment a single rate-limit counter row."""
    window_start_threshold = now - timedelta(seconds=window_seconds)
    rate_exceeded_info = None

    with transaction.atomic():
        rate_limit = _get_or_create_locked_record(model, now, **lookup)

        if rate_limit.window_start < window_start_threshold:
            rate_limit.request_count = 1
            rate_limit.window_start = now
            rate_limit.last_exceeded_at = None
            rate_limit.save(update_fields=['request_count', 'window_start', 'last_exceeded_at'])
            return True

        if rate_limit.request_count >= max_requests:
            rate_limit.last_exceeded_at = now
            rate_limit.save(update_fields=['last_exceeded_at'])
            window_end = rate_limit.window_start + timedelta(seconds=window_seconds)
            retry_after = int((window_end - now).total_seconds())
            rate_exceeded_info = max(1, retry_after)
        else:
            rate_limit.request_count += 1
            rate_limit.save(update_fields=['request_count'])

    if rate_exceeded_info is not None:
        raise RateLimitExceeded(
            retry_after_seconds=rate_exceeded_info,
            message=f"Rate limit exceeded. Try again in {rate_exceeded_info} seconds."
        )
    return True


def _check_ip_rate_limit(ip_address: str, max_requests: int, window_seconds: int) -> bool:
    from .models import ChatRateLimit

    return _check_rate_limit_record(
        ChatRateLimit,
        timezone.now(),
        max_requests,
        window_seconds,
        ip_address=ip_address,
    )


def _check_user_rate_limit(user, max_requests: int, window_seconds: int) -> bool:
    from .models import ChatRateLimitUser

    return _check_rate_limit_record(
        ChatRateLimitUser,
        timezone.now(),
        max_requests,
        window_seconds,
        user=user,
    )


def check_rate_limit(ip_address: str, user=None) -> bool:
    """
    Check and increment rate limit for the current request.

    Anonymous requests are tracked by IP.
    Authenticated requests are tracked by user.
    """
    max_requests, window_seconds = get_rate_limit_settings(user)
    if user is not None and getattr(user, 'is_authenticated', False):
        return _check_user_rate_limit(user, max_requests, window_seconds)
    return _check_ip_rate_limit(ip_address, max_requests, window_seconds)


def format_retry_after_human(seconds: int, language: str = 'en') -> str:
    """Format retry_after seconds into human-readable string with localization"""
    if language == 'es':
        if seconds < 60:
            return f"{seconds} segundo{'s' if seconds != 1 else ''}"
        elif seconds < 3600:
            minutes = seconds // 60
            return f"{minutes} minuto{'s' if minutes != 1 else ''}"
        else:
            hours = seconds // 3600
            minutes = (seconds % 3600) // 60
            if minutes > 0:
                return f"{hours} hora{'s' if hours != 1 else ''} y {minutes} minuto{'s' if minutes != 1 else ''}"
            return f"{hours} hora{'s' if hours != 1 else ''}"
    else:
        # Default to English
        if seconds < 60:
            return f"{seconds} second{'s' if seconds != 1 else ''}"
        elif seconds < 3600:
            minutes = seconds // 60
            return f"{minutes} minute{'s' if minutes != 1 else ''}"
        else:
            hours = seconds // 3600
            minutes = (seconds % 3600) // 60
            if minutes > 0:
                return f"{hours} hour{'s' if hours != 1 else ''} and {minutes} minute{'s' if minutes != 1 else ''}"
            return f"{hours} hour{'s' if hours != 1 else ''}"
