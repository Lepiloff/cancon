"""
Rate limiting logic for chat endpoint.

Uses PostgreSQL for storage with atomic counters and row-level locking.
"""

from django.conf import settings
from django.db import transaction
from django.utils import timezone
from datetime import timedelta


class RateLimitExceeded(Exception):
    """Raised when rate limit is exceeded"""

    def __init__(self, retry_after_seconds: int, message: str = "Rate limit exceeded"):
        self.retry_after_seconds = retry_after_seconds
        self.message = message
        super().__init__(self.message)


def get_rate_limit_settings():
    """Get rate limit configuration from settings"""
    max_requests = getattr(settings, 'CHAT_RATE_LIMIT_MAX_REQUESTS', 10)
    window_seconds = getattr(settings, 'CHAT_RATE_LIMIT_WINDOW_SECONDS', 3600)
    return max_requests, window_seconds


def check_rate_limit(ip_address: str) -> bool:
    """
    Check and increment rate limit for an IP address.

    Uses atomic operations with row-level locking to ensure thread safety.

    Args:
        ip_address: The client IP address

    Returns:
        True if request is allowed

    Raises:
        RateLimitExceeded: If rate limit is exceeded
    """
    from .models import ChatRateLimit

    max_requests, window_seconds = get_rate_limit_settings()
    now = timezone.now()
    window_start_threshold = now - timedelta(seconds=window_seconds)

    # Store rate limit exceeded info to raise after transaction commits
    rate_exceeded_info = None

    with transaction.atomic():
        # Try to get existing record with row-level lock
        rate_limit = ChatRateLimit.objects.select_for_update().filter(
            ip_address=ip_address
        ).first()

        if rate_limit is None:
            # No record exists, create new one
            ChatRateLimit.objects.create(
                ip_address=ip_address,
                request_count=1,
                window_start=now
            )
            return True

        # Check if window has expired
        if rate_limit.window_start < window_start_threshold:
            # Reset the counter for new window
            rate_limit.request_count = 1
            rate_limit.window_start = now
            rate_limit.save(update_fields=['request_count', 'window_start'])
            return True

        # Window is still active, check limit
        if rate_limit.request_count >= max_requests:
            # Rate limit exceeded
            rate_limit.last_exceeded_at = now
            rate_limit.save(update_fields=['last_exceeded_at'])

            # Calculate retry_after - seconds until window expires
            window_end = rate_limit.window_start + timedelta(seconds=window_seconds)
            retry_after = int((window_end - now).total_seconds())
            retry_after = max(1, retry_after)  # At least 1 second

            # Store info to raise exception after transaction commits
            rate_exceeded_info = retry_after
        else:
            # Increment counter
            rate_limit.request_count += 1
            rate_limit.save(update_fields=['request_count'])

    # Raise exception outside of transaction block so last_exceeded_at is saved
    if rate_exceeded_info is not None:
        raise RateLimitExceeded(
            retry_after_seconds=rate_exceeded_info,
            message=f"Rate limit exceeded. Try again in {rate_exceeded_info} seconds."
        )

    return True


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
