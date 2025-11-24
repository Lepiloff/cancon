from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import ChatConfiguration, APIKey, ChatSession, ChatMessage


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


# Custom admin site configuration
admin.site.site_header = "Canna AI Budtender Admin"
admin.site.site_title = "AI Budtender Admin"
admin.site.index_title = "Welcome to AI Budtender Administration"