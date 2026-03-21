"""
Export chat sessions to JSONL format for LLM-driven analysis.

Usage:
    python manage.py export_chat_logs --since=30d --output=/tmp/chat_analysis.jsonl
    python manage.py export_chat_logs --since=2026-03-01 --language=es
    python manage.py export_chat_logs --since=7d | head -5
"""

import json
import sys
from datetime import datetime, timedelta
from typing import IO

from django.core.management.base import BaseCommand, CommandError
from django.db.models import Count
from django.utils import timezone

from apps.chat_bot.models import ChatMessage, ChatSession


def parse_since(value: str) -> datetime:
    """Parse --since value: YYYY-MM-DD, 'today', 'yesterday', or relative like '7d', '30d'."""
    now = timezone.now()
    if value == 'today':
        return now.replace(hour=0, minute=0, second=0, microsecond=0)
    if value == 'yesterday':
        return (now - timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    if value.endswith('d') and value[:-1].isdigit():
        days = int(value[:-1])
        return now - timedelta(days=days)
    try:
        dt = datetime.strptime(value, '%Y-%m-%d')
        return timezone.make_aware(dt) if timezone.is_naive(dt) else dt
    except ValueError:
        raise CommandError(f"Invalid --since value: '{value}'. Use YYYY-MM-DD, 'today', 'yesterday', or '7d'/'30d'.")


def build_session_record(session: ChatSession) -> dict | None:
    """Build a JSONL-compatible dict for a single session."""
    messages_qs = ChatMessage.objects.filter(
        session=session,
        message_type__in=['user', 'ai'],
    ).order_by('timestamp')

    messages = []
    for msg in messages_qs:
        entry = {
            'role': 'user' if msg.message_type == 'user' else 'assistant',
            'content': msg.content,
            'timestamp': msg.timestamp.isoformat(),
        }
        if msg.message_type == 'ai':
            if msg.detected_intent:
                entry['intent'] = msg.detected_intent
            if msg.confidence_score is not None:
                entry['confidence'] = msg.confidence_score
            if msg.recommended_strains:
                strains = msg.recommended_strains
                if isinstance(strains, list):
                    entry['strains'] = [
                        s.get('name', s) if isinstance(s, dict) else s
                        for s in strains
                    ]
            if msg.api_response_time_ms is not None:
                entry['response_time_ms'] = msg.api_response_time_ms
        messages.append(entry)

    if not messages:
        return None

    duration_minutes = None
    if session.last_activity_at and session.started_at:
        delta = session.last_activity_at - session.started_at
        duration_minutes = round(delta.total_seconds() / 60, 1)

    return {
        'session_id': str(session.session_id),
        'language': session.language or '',
        'ip': session.ip_address,
        'user': session.user.email if session.user else None,
        'started_at': session.started_at.isoformat(),
        'duration_minutes': duration_minutes,
        'exchanges': len([m for m in messages if m['role'] == 'user']),
        'messages': messages,
    }


def export_sessions_jsonl(
    out: IO,
    since: datetime | None = None,
    until: datetime | None = None,
    min_messages: int = 2,
    language: str | None = None,
) -> int:
    """Export matching sessions to JSONL. Returns count of exported sessions."""
    qs = ChatSession.objects.select_related('user')

    if since:
        qs = qs.filter(started_at__gte=since)
    if until:
        qs = qs.filter(started_at__lte=until)
    if language:
        qs = qs.filter(language=language)
    if min_messages > 0:
        qs = qs.annotate(msg_count=Count('messages')).filter(msg_count__gte=min_messages)

    qs = qs.order_by('started_at')

    count = 0
    for session in qs.iterator():
        record = build_session_record(session)
        if record:
            out.write(json.dumps(record, ensure_ascii=False, default=str))
            out.write('\n')
            count += 1

    return count


class Command(BaseCommand):
    help = 'Export chat sessions to JSONL format for LLM analysis'

    def add_arguments(self, parser):
        parser.add_argument(
            '--since',
            type=str,
            required=True,
            help="Start date: YYYY-MM-DD, 'today', 'yesterday', '7d', '30d'",
        )
        parser.add_argument(
            '--until',
            type=str,
            default=None,
            help='End date: YYYY-MM-DD (default: now)',
        )
        parser.add_argument(
            '--output',
            type=str,
            default=None,
            help='Output file path (default: stdout)',
        )
        parser.add_argument(
            '--min-messages',
            type=int,
            default=2,
            help='Minimum messages per session to include (default: 2)',
        )
        parser.add_argument(
            '--language',
            type=str,
            default=None,
            choices=['es', 'en'],
            help='Filter by session language',
        )

    def handle(self, *args, **options):
        since = parse_since(options['since'])

        until = None
        if options['until']:
            until = parse_since(options['until'])

        output_path = options['output']
        min_messages = options['min_messages']
        language = options['language']

        if output_path:
            with open(output_path, 'w', encoding='utf-8') as f:
                count = export_sessions_jsonl(f, since, until, min_messages, language)
            self.stderr.write(self.style.SUCCESS(
                f'Exported {count} session(s) to {output_path}'
            ))
        else:
            count = export_sessions_jsonl(sys.stdout, since, until, min_messages, language)
            self.stderr.write(self.style.SUCCESS(f'Exported {count} session(s)'))
