"""
Archive and delete old chat messages for data retention.

Two-phase cleanup: export to JSONL archive, then delete from DB.
ChatSession rows are kept (lightweight metadata).

Usage:
    python manage.py cleanup_chat_messages --days=90
    python manage.py cleanup_chat_messages --days=90 --dry-run
    python manage.py cleanup_chat_messages --days=30 --archive-dir=/tmp/archives
    python manage.py cleanup_chat_messages --days=0 --no-archive  # delete all, no export
"""

import json
import os
from datetime import date, timedelta
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db.models import Count
from django.utils import timezone

from apps.chat_bot.management.commands.export_chat_logs import (
    build_session_record,
    export_sessions_jsonl,
)
from apps.chat_bot.models import ChatMessage, ChatSession


class Command(BaseCommand):
    help = 'Archive old chat messages to JSONL and delete from database'

    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=90,
            help='Retention period in days (default: 90). Messages older than this are archived and deleted.',
        )
        parser.add_argument(
            '--archive-dir',
            type=str,
            default=None,
            help='Override archive directory (default: BASE_DIR/data/chat_archives/)',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be archived/deleted without doing it',
        )
        parser.add_argument(
            '--no-archive',
            action='store_true',
            help='Skip JSONL export, just delete messages (use with caution)',
        )

    def handle(self, *args, **options):
        days = options['days']
        dry_run = options['dry_run']
        no_archive = options['no_archive']

        cutoff = timezone.now() - timedelta(days=days)

        # Find messages older than cutoff
        old_messages = ChatMessage.objects.filter(timestamp__lt=cutoff)
        message_count = old_messages.count()

        if message_count == 0:
            self.stdout.write(self.style.SUCCESS('No messages older than the retention period.'))
            return

        # Find affected sessions (sessions that have old messages)
        session_ids = old_messages.values_list('session_id', flat=True).distinct()
        sessions = ChatSession.objects.filter(
            id__in=session_ids,
        ).select_related('user')
        session_count = sessions.count()

        # Estimate size
        estimated_kb = round(message_count * 2.5, 1)  # ~2.5KB per message avg

        if dry_run:
            self.stdout.write(self.style.WARNING(
                f'DRY RUN: Would archive and delete {message_count} message(s) '
                f'from {session_count} session(s), ~{estimated_kb} KB'
            ))
            self.stdout.write(f'  Cutoff: {cutoff.isoformat()}')
            self.stdout.write(f'  Retention: {days} day(s)')
            return

        # Phase 1: Export to JSONL archive
        archive_path = None
        if not no_archive:
            archive_dir = options['archive_dir']
            if archive_dir:
                archive_dir = Path(archive_dir)
            else:
                archive_dir = getattr(
                    settings, 'CHAT_ARCHIVE_DIR',
                    Path(settings.BASE_DIR) / 'data' / 'chat_archives'
                )
                archive_dir = Path(archive_dir)

            archive_dir.mkdir(parents=True, exist_ok=True)
            archive_path = archive_dir / f'chat_archive_{date.today().isoformat()}.jsonl'

            # Export sessions that have old messages
            exported = 0
            with open(archive_path, 'a', encoding='utf-8') as f:
                for session in sessions.iterator():
                    record = build_session_record(session)
                    if record:
                        f.write(json.dumps(record, ensure_ascii=False, default=str))
                        f.write('\n')
                        exported += 1

            self.stdout.write(
                f'Archived {exported} session(s) to {archive_path}'
            )

        # Phase 2: Delete old messages from DB (keep ChatSession rows)
        deleted_count, _ = old_messages.delete()

        self.stdout.write(self.style.SUCCESS(
            f'Deleted {deleted_count} message(s) from {session_count} session(s), '
            f'freed ~{estimated_kb} KB'
        ))
        if archive_path:
            self.stdout.write(f'Archive: {archive_path}')
