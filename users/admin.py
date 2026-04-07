from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .forms import CustomUserCreationForm, CustomUserChangeForm
from .models import ConsumptionNote, CustomUser


class CustomUserAdmin(UserAdmin):
    add_form = CustomUserCreationForm
    form = CustomUserChangeForm
    model = CustomUser
    list_display = ("display_name", "email", "is_staff", "is_active",)
    list_filter = ("email", "is_staff", "is_active",)
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Permissions", {"fields": ("is_staff", "is_active", "groups", "user_permissions")}),
    )
    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": (
                "email", "password1", "password2", "is_staff",
                "is_active", "groups", "user_permissions"
            )}
        ),
    )
    search_fields = ("email",)
    ordering = ("email",)

    @admin.display(ordering="email", description="Display name")
    def display_name(self, obj):
        return obj.email.split("@")[0]


@admin.register(ConsumptionNote)
class ConsumptionNoteAdmin(admin.ModelAdmin):
    list_display = ("user", "strain_label", "date", "method", "created_at")
    list_filter = ("method", "date", "created_at")
    search_fields = ("user__email", "strain__name", "strain_name_text", "notes")
    raw_id_fields = ("user", "strain")
    ordering = ("-date", "-created_at")

    @admin.display(ordering="strain__name", description="Strain")
    def strain_label(self, obj):
        return obj.strain.name if obj.strain else obj.strain_name_text or "-"


admin.site.register(CustomUser, CustomUserAdmin)
