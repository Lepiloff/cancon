import json
from io import StringIO

from django.contrib import admin
from django.http import HttpResponse
from django.utils.html import format_html
from django.utils import timezone
from django.conf import settings
from datetime import timedelta

from .models import ChatConfiguration, APIKey, ChatSession, ChatMessage, ChatRateLimit


@admin.register(ChatConfiguration)
class ChatConfigurationAdmin(admin.ModelAdmin):
    list_display = ['__str__', 'is_active', 'api_base_url', 'max_history', 'updated_at']
    list_editable = ['is_active']
    fieldsets = [
        ('API Configuration', {
            'fields': ['api_base_url', 'api_key', 'websocket_url']
        }),
        ('Chat Settings', {
            'fields': ['max_history', 'is_active']
        }),
        ('Timestamps', {
            'fields': ['created_at', 'updated_at'],
            'classes': ['collapse']
        })
    ]
    readonly_fields = ['created_at', 'updated_at']

    def has_delete_permission(self, request, obj=None):
        return False  # Don't allow deletion of the config

    def has_add_permission(self, request):
        # Only allow one configuration
        return not ChatConfiguration.objects.exists()


@admin.register(APIKey)
class APIKeyAdmin(admin.ModelAdmin):
    list_display = ['name', 'key_preview', 'is_active', 'usage_count', 'last_used_at', 'created_at']
    list_filter = ['is_active', 'created_at', 'last_used_at']
    search_fields = ['name', 'key']
    list_editable = ['is_active']
    readonly_fields = ['key', 'usage_count', 'last_used_at', 'created_at']
    fieldsets = [
        (None, {
            'fields': ['name', 'key', 'is_active']
        }),
        ('Security', {
            'fields': ['allowed_origins']
        }),
        ('Usage Statistics', {
            'fields': ['usage_count', 'last_used_at', 'created_at'],
            'classes': ['collapse']
        })
    ]

    def key_preview(self, obj):
        if obj.key:
            return f"{obj.key[:8]}...{obj.key[-4:]}"
        return "-"
    key_preview.short_description = "API Key"

    def get_readonly_fields(self, request, obj=None):
        if obj:  # Editing existing object
            return self.readonly_fields
        else:  # Adding new object
            return ['usage_count', 'last_used_at', 'created_at']


def _build_session_jsonl(session: ChatSession) -> dict | None:
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


@admin.register(ChatSession)
class ChatSessionAdmin(admin.ModelAdmin):
    list_display = [
        'session_preview', 'user', 'ip_address', 'language',
        'message_count', 'is_active', 'duration', 'started_at', 'last_activity_at',
    ]
    list_filter = ['is_active', 'language', 'started_at', 'last_activity_at']
    search_fields = ['session_id', 'user__email', 'ip_address']
    readonly_fields = ['session_id', 'started_at', 'last_activity_at', 'duration']
    date_hierarchy = 'started_at'
    actions = ['download_jsonl']

    def session_preview(self, obj):
        return f"{obj.session_id.hex[:8]}..."
    session_preview.short_description = "Session ID"

    def duration(self, obj):
        if obj.last_activity_at and obj.started_at:
            delta = obj.last_activity_at - obj.started_at
            total_seconds = int(delta.total_seconds())
            if total_seconds < 60:
                return f"{total_seconds}s"
            minutes = total_seconds // 60
            if minutes < 60:
                return f"{minutes}m"
            hours = minutes // 60
            remaining = minutes % 60
            return f"{hours}h {remaining}m"
        return "-"
    duration.short_description = "Duration"

    fieldsets = [
        ('Session Info', {
            'fields': ['session_id', 'user', 'ip_address', 'user_agent', 'language']
        }),
        ('Activity', {
            'fields': ['started_at', 'last_activity_at', 'duration', 'message_count', 'is_active']
        }),
        ('API', {
            'fields': ['api_key'],
            'classes': ['collapse']
        })
    ]

    @admin.action(description='Download JSONL')
    def download_jsonl(self, request, queryset):
        buf = StringIO()
        count = 0
        for session in queryset.select_related('user').order_by('started_at'):
            record = _build_session_jsonl(session)
            if record:
                buf.write(json.dumps(record, ensure_ascii=False, default=str))
                buf.write('\n')
                count += 1

        response = HttpResponse(buf.getvalue(), content_type='application/x-ndjson')
        response['Content-Disposition'] = 'attachment; filename="chat_sessions.jsonl"'
        self.message_user(request, f'Exported {count} session(s) to JSONL.')
        return response


@admin.register(ChatRateLimit)
class ChatRateLimitAdmin(admin.ModelAdmin):
    list_display = ['ip_address', 'request_count', 'window_start', 'is_expired', 'last_exceeded_at']
    list_filter = ['last_exceeded_at']
    search_fields = ['ip_address']
    readonly_fields = ['ip_address', 'request_count', 'window_start', 'last_exceeded_at']
    date_hierarchy = 'window_start'
    ordering = ['-window_start']
    actions = ['reset_rate_limits', 'delete_expired_records']

    def is_expired(self, obj):
        """Check if the rate limit window has expired"""
        window_seconds = getattr(settings, 'CHAT_RATE_LIMIT_WINDOW_SECONDS', 3600)
        window_start_threshold = timezone.now() - timedelta(seconds=window_seconds)
        expired = obj.window_start < window_start_threshold
        if expired:
            return format_html('<span style="color: #999;">Expired</span>')
        return format_html('<span style="color: #28a745;">Active</span>')
    is_expired.short_description = 'Status'

    def has_add_permission(self, request):
        return False  # Records are created automatically

    @admin.action(description='Reset selected rate limits (set count to 0)')
    def reset_rate_limits(self, request, queryset):
        updated = queryset.update(request_count=0, window_start=timezone.now())
        self.message_user(request, f'Reset {updated} rate limit(s).')

    @admin.action(description='Delete expired rate limit records')
    def delete_expired_records(self, request, queryset):
        window_seconds = getattr(settings, 'CHAT_RATE_LIMIT_WINDOW_SECONDS', 3600)
        window_start_threshold = timezone.now() - timedelta(seconds=window_seconds)
        expired_records = queryset.filter(window_start__lt=window_start_threshold)
        count = expired_records.count()
        expired_records.delete()
        self.message_user(request, f'Deleted {count} expired rate limit record(s).')

    fieldsets = [
        ('Rate Limit Info', {
            'fields': ['ip_address', 'request_count', 'window_start', 'last_exceeded_at']
        }),
    ]


# Custom admin site configuration
admin.site.site_header = "Canna AI Budtender Admin"
admin.site.site_title = "AI Budtender Admin"
admin.site.index_title = "Welcome to AI Budtender Administration"
