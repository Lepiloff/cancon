from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.utils import timezone
from django.conf import settings
from datetime import timedelta
from .models import ChatConfiguration, APIKey, ChatSession, ChatMessage, ChatRateLimit


@admin.register(ChatConfiguration)
class ChatConfigurationAdmin(admin.ModelAdmin):
    list_display = ['__str__', 'is_active', 'api_base_url', 'max_history', 'rate_limit', 'updated_at']
    list_editable = ['is_active']
    fieldsets = [
        ('API Configuration', {
            'fields': ['api_base_url', 'api_key', 'websocket_url']
        }),
        ('Chat Settings', {
            'fields': ['max_history', 'rate_limit', 'is_active']
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


class ChatMessageInline(admin.TabularInline):
    model = ChatMessage
    extra = 0
    readonly_fields = ['message_type', 'content', 'timestamp', 'response_time_ms']
    fields = ['message_type', 'content', 'timestamp', 'response_time_ms']
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(ChatSession)
class ChatSessionAdmin(admin.ModelAdmin):
    list_display = ['session_preview', 'user', 'ip_address', 'message_count', 'is_active', 'started_at', 'last_activity_at']
    list_filter = ['is_active', 'started_at', 'last_activity_at']
    search_fields = ['session_id', 'user__email', 'ip_address']
    readonly_fields = ['session_id', 'started_at', 'last_activity_at']
    inlines = [ChatMessageInline]
    date_hierarchy = 'started_at'

    def session_preview(self, obj):
        return f"{obj.session_id.hex[:8]}..."
    session_preview.short_description = "Session ID"

    fieldsets = [
        ('Session Info', {
            'fields': ['session_id', 'user', 'ip_address', 'user_agent']
        }),
        ('Activity', {
            'fields': ['started_at', 'last_activity_at', 'message_count', 'is_active']
        }),
        ('API', {
            'fields': ['api_key'],
            'classes': ['collapse']
        })
    ]


@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ['session_preview', 'message_type', 'content_preview', 'timestamp', 'response_time_ms']
    list_filter = ['message_type', 'timestamp', 'session__is_active']
    search_fields = ['content', 'session__session_id', 'session__ip_address']
    readonly_fields = ['session', 'timestamp', 'recommended_strains_display']
    date_hierarchy = 'timestamp'

    def session_preview(self, obj):
        return f"{obj.session.session_id.hex[:8]}..."
    session_preview.short_description = "Session"

    def content_preview(self, obj):
        return obj.content[:100] + "..." if len(obj.content) > 100 else obj.content
    content_preview.short_description = "Content"

    def recommended_strains_display(self, obj):
        if obj.recommended_strains:
            strains = obj.recommended_strains
            if isinstance(strains, list) and strains:
                strain_names = [strain.get('name', 'Unknown') for strain in strains[:3]]
                display = ", ".join(strain_names)
                if len(strains) > 3:
                    display += f" and {len(strains) - 3} more"
                return display
        return "No strains recommended"
    recommended_strains_display.short_description = "Recommended Strains"

    fieldsets = [
        ('Message Details', {
            'fields': ['session', 'message_type', 'content', 'timestamp']
        }),
        ('AI Response Data', {
            'fields': ['recommended_strains_display'],
            'classes': ['collapse']
        }),
        ('Performance', {
            'fields': ['response_time_ms', 'api_response_time_ms'],
            'classes': ['collapse']
        }),
        ('Metadata', {
            'fields': ['ip_address'],
            'classes': ['collapse']
        })
    ]


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