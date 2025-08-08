from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
import uuid

User = get_user_model()


class ChatConfiguration(models.Model):
    """Configuration settings for AI Budtender chat"""
    
    api_base_url = models.URLField(
        default='http://localhost:8001',
        help_text='Base URL for the canagent API service'
    )
    api_key = models.CharField(
        max_length=255,
        blank=True,
        help_text='API key for authentication with canagent service'
    )
    websocket_url = models.URLField(
        blank=True,
        null=True,
        help_text='WebSocket URL for real-time messaging (optional)'
    )
    max_history = models.PositiveIntegerField(
        default=10,
        help_text='Maximum number of conversation messages to keep in memory'
    )
    rate_limit = models.PositiveIntegerField(
        default=60,
        help_text='Number of requests per minute allowed per user'
    )
    is_active = models.BooleanField(
        default=True,
        help_text='Enable/disable the chat widget'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Chat Configuration'
        verbose_name_plural = 'Chat Configuration'
    
    def __str__(self):
        return f"Chat Config - {'Active' if self.is_active else 'Inactive'}"
    
    @classmethod
    def get_config(cls):
        """Get the current chat configuration"""
        config, created = cls.objects.get_or_create(pk=1)
        return config


class APIKey(models.Model):
    """API keys for chat bot authentication"""
    
    name = models.CharField(max_length=100, help_text='Descriptive name for this API key')
    key = models.CharField(max_length=64, unique=True, default=uuid.uuid4)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_used_at = models.DateTimeField(blank=True, null=True)
    usage_count = models.PositiveIntegerField(default=0)
    
    # Optional: Link to specific domains or IPs
    allowed_origins = models.TextField(
        blank=True,
        help_text='Comma-separated list of allowed origins (domains/IPs). Leave blank for all.'
    )
    
    class Meta:
        verbose_name = 'API Key'
        verbose_name_plural = 'API Keys'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.name} ({'Active' if self.is_active else 'Inactive'})"
    
    def save(self, *args, **kwargs):
        if not self.key:
            self.key = str(uuid.uuid4()).replace('-', '')
        super().save(*args, **kwargs)
    
    def mark_used(self):
        """Mark this API key as used"""
        self.last_used_at = timezone.now()
        self.usage_count += 1
        self.save(update_fields=['last_used_at', 'usage_count'])


class ChatSession(models.Model):
    """Track chat sessions for analytics"""
    
    session_id = models.UUIDField(default=uuid.uuid4, unique=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, blank=True, null=True)
    ip_address = models.GenericIPAddressField()
    user_agent = models.TextField(blank=True)
    
    # Session metadata
    started_at = models.DateTimeField(auto_now_add=True)
    last_activity_at = models.DateTimeField(auto_now=True)
    message_count = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    
    # Optional: Track which API key was used
    api_key = models.ForeignKey(APIKey, on_delete=models.SET_NULL, blank=True, null=True)
    
    class Meta:
        verbose_name = 'Chat Session'
        verbose_name_plural = 'Chat Sessions'
        ordering = ['-started_at']
    
    def __str__(self):
        user_info = f"User: {self.user}" if self.user else f"IP: {self.ip_address}"
        return f"Session {self.session_id.hex[:8]} - {user_info}"


class ChatMessage(models.Model):
    """Store chat messages for analytics and improvement"""
    
    MESSAGE_TYPES = [
        ('user', 'User Message'),
        ('ai', 'AI Response'),
        ('system', 'System Message'),
        ('error', 'Error Message')
    ]
    
    session = models.ForeignKey(ChatSession, on_delete=models.CASCADE, related_name='messages')
    message_type = models.CharField(max_length=10, choices=MESSAGE_TYPES)
    content = models.TextField()
    
    # For AI responses, store recommended strains
    recommended_strains = models.JSONField(blank=True, null=True)
    
    # Performance tracking
    response_time_ms = models.PositiveIntegerField(blank=True, null=True)
    api_response_time_ms = models.PositiveIntegerField(blank=True, null=True)
    
    # Metadata
    timestamp = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField()
    
    class Meta:
        verbose_name = 'Chat Message'
        verbose_name_plural = 'Chat Messages'
        ordering = ['timestamp']
    
    def __str__(self):
        return f"{self.get_message_type_display()} - {self.content[:50]}..."


class ChatFeedback(models.Model):
    """User feedback on AI responses"""
    
    FEEDBACK_TYPES = [
        ('thumbs_up', 'Thumbs Up'),
        ('thumbs_down', 'Thumbs Down'),
        ('helpful', 'Helpful'),
        ('not_helpful', 'Not Helpful')
    ]
    
    message = models.ForeignKey(ChatMessage, on_delete=models.CASCADE, related_name='feedback')
    feedback_type = models.CharField(max_length=20, choices=FEEDBACK_TYPES)
    comment = models.TextField(blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField()
    
    class Meta:
        verbose_name = 'Chat Feedback'
        verbose_name_plural = 'Chat Feedback'
        unique_together = ['message', 'ip_address']  # One feedback per message per IP
    
    def __str__(self):
        return f"{self.get_feedback_type_display()} - {self.message.content[:30]}..."