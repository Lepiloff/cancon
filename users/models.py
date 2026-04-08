from django.conf import settings
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from .managers import CustomUserManager


class CustomUser(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(_("email address"), unique=True)
    display_name = models.CharField(_("display name"), max_length=50, blank=True)
    is_staff = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    date_joined = models.DateTimeField(default=timezone.now)
    cookie_consent = models.JSONField(
        default=dict,
        blank=True,
        help_text=_("Cookie consent preferences"),
    )
    cookie_consent_date = models.DateTimeField(null=True, blank=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    objects = CustomUserManager()

    def get_display_name(self):
        display_name = (self.display_name or "").strip()
        if display_name:
            return display_name
        return (self.email or "").split("@")[0]

    def get_public_display_name(self):
        display_name = (self.display_name or "").strip()
        if display_name:
            return display_name

        local_part = (self.email or "").split("@")[0].strip()
        if not local_part:
            return _("Anonymous")
        if len(local_part) <= 2:
            return f"{local_part[:1]}***"
        if len(local_part) <= 4:
            return f"{local_part[:2]}***"
        return f"{local_part[:2]}***{local_part[-1]}"

    def __str__(self):
        return self.email


class ConsumptionNote(models.Model):
    METHOD_CHOICES = [
        ('smoke', _('Fumar')),
        ('vape', _('Vapear')),
        ('edible', _('Comestible')),
        ('tincture', _('Tintura')),
        ('topical', _('Tópico')),
        ('other', _('Otro')),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='consumption_notes',
    )
    strain = models.ForeignKey(
        'strains.Strain',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='consumption_notes',
    )
    strain_name_text = models.CharField(max_length=255, blank=True)
    date = models.DateField()
    notes = models.TextField(max_length=5000, blank=True)
    method = models.CharField(max_length=20, choices=METHOD_CHOICES, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-date', '-created_at']
        indexes = [
            models.Index(fields=['user', 'date'], name='cons_note_user_date_idx'),
        ]

    @property
    def strain_label(self):
        if self.strain:
            return self.strain.name
        return self.strain_name_text or _('Nota sin título')

    def __str__(self):
        return f"{self.user_id}:{self.strain_label}:{self.date}"
