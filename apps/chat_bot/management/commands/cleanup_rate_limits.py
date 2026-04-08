"""
Management command to clean up expired rate limit records.

Usage:
    python manage.py cleanup_rate_limits           # Delete expired records
    python manage.py cleanup_rate_limits --dry-run # Show what would be deleted
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from django.conf import settings
from datetime import timedelta

from apps.chat_bot.models import ChatRateLimit, ChatRateLimitUser


class Command(BaseCommand):
    help = 'Delete expired rate limit records from the database'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be deleted without actually deleting',
        )
        parser.add_argument(
            '--hours',
            type=int,
            default=None,
            help='Override window hours (default: uses CHAT_RATE_LIMIT_WINDOW_SECONDS setting)',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        hours_override = options['hours']

        # Determine window duration
        if hours_override is not None:
            window_seconds = hours_override * 3600
        else:
            window_seconds = getattr(settings, 'CHAT_RATE_LIMIT_WINDOW_SECONDS', 3600)

        # Calculate threshold
        threshold = timezone.now() - timedelta(seconds=window_seconds)

        # Find expired records
        expired_ip_records = ChatRateLimit.objects.filter(window_start__lt=threshold)
        expired_user_records = ChatRateLimitUser.objects.filter(window_start__lt=threshold)
        ip_count = expired_ip_records.count()
        user_count = expired_user_records.count()
        count = ip_count + user_count

        if count == 0:
            self.stdout.write(self.style.SUCCESS('No expired rate limit records found.'))
            return

        if dry_run:
            self.stdout.write(self.style.WARNING(f'DRY RUN: Would delete {count} expired record(s):'))
            for record in expired_ip_records[:10]:
                self.stdout.write(f'  - IP {record.ip_address} (last active: {record.window_start})')
            for record in expired_user_records[:10]:
                self.stdout.write(f'  - User {record.user.email} (last active: {record.window_start})')
            if count > 20:
                self.stdout.write(f'  ... and {count - 20} more')
        else:
            expired_ip_records.delete()
            expired_user_records.delete()
            self.stdout.write(self.style.SUCCESS(f'Deleted {count} expired rate limit record(s).'))
