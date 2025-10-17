from django import forms
from django.contrib import admin
from django.utils.html import format_html
from modeltranslation.admin import TranslationAdmin
from apps.strains.models import (
    AlternativeStrainName,
    Article,
    ArticleCategory,
    ArticleImage,
    Strain,
    Feeling,
    Negative,
    HelpsWith,
    Flavor,
    Terpene,
)
from apps.strains.signals import perform_translation


# ========== Admin Forms ==========


class TranslatedModelForm(forms.ModelForm):
    """Base form for models with translation support (DRY principle)."""

    skip_translation = forms.BooleanField(
        required=False,
        initial=False,
        label='Skip translation (minor edit)',
        help_text='✓ Check this if you made small changes (typo, formatting) and don\'t need re-translation. '
                  'Leave unchecked for content changes that need translation.',
    )


class StrainAdminForm(TranslatedModelForm):
    class Meta:
        model = Strain
        fields = '__all__'


class ArticleAdminForm(TranslatedModelForm):
    class Meta:
        model = Article
        fields = '__all__'


class TerpeneAdminForm(TranslatedModelForm):
    class Meta:
        model = Terpene
        fields = '__all__'


class TranslatedModelAdmin(TranslationAdmin):
    """Base admin class for models with translation support (DRY principle)"""

    def save_model(self, request, obj, form, change):
        """
        Handle skip_translation checkbox for all translated models.

        If checkbox is checked:
        - Sets flag to bypass translation check in signals
        - Updates hash to match new content (prevents 'outdated' status)
        """
        if form.cleaned_data.get('skip_translation'):
            obj._skip_translation_check = True
            obj.translation_source_hash = obj.get_translatable_content_hash()

        super().save_model(request, obj, form, change)

    def translation_status_badge(self, obj):
        """Display colored badge for translation status"""
        colors = {
            'synced': '#28a745',
            'pending': '#ffc107',
            'outdated': '#dc3545',
            'failed': '#6c757d',
        }
        color = colors.get(obj.translation_status, '#6c757d')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 3px; font-weight: bold;">{}</span>',
            color,
            obj.get_translation_status_display()
        )
    translation_status_badge.short_description = 'Translation Status'


class AlternativeNameInline(admin.TabularInline):
    model = AlternativeStrainName
    extra = 1


class StrainAdmin(TranslatedModelAdmin):
    form = StrainAdminForm
    list_display = (
        'name',
        'category',
        'rating',
        'thc',
        'cbd',
        'cbg',
        'translation_status_badge',
        'last_translated_at',
        'active',
        'main',
        'top',
        'is_review'
    )
    search_fields = ('name', 'category')  # name is NOT translated
    list_filter = ('category', 'active')
    filter_horizontal = ('feelings', 'negatives', 'helps_with', 'flavors')
    list_editable = ('active', 'main', 'top', 'is_review')
    inlines = [AlternativeNameInline]
    actions = ['force_retranslate']

    @admin.action(description='Force retranslate selected items')
    def force_retranslate(self, request, queryset):
        """Force retranslate selected items"""
        count = 0
        for obj in queryset:
            success = perform_translation(obj, 'Strain')
            if success:
                count += 1

        self.message_user(request, f'{count} strains translated successfully')


class ArticleImageInline(admin.TabularInline):
    model = ArticleImage
    extra = 1


class ArticleAdmin(TranslatedModelAdmin):
    form = ArticleAdminForm
    inlines = [ArticleImageInline]
    list_display = ('title_display', 'translation_status_badge', 'last_translated_at')
    search_fields = ('title_en', 'title_es')
    list_filter = ('category',)
    actions = ['force_retranslate']

    def title_display(self, obj):
        """Display title with both languages when available"""
        en = obj.title_en or ''
        es = obj.title_es or ''

        if en and es:
            return f'🇬🇧 {en[:50]} / 🇪🇸 {es[:50]}'
        elif en:
            return f'🇬🇧 {en[:50]}'
        elif es:
            return f'🇪🇸 {es[:50]}'
        return '-'
    title_display.short_description = 'Title'

    @admin.action(description='Force retranslate selected items')
    def force_retranslate(self, request, queryset):
        """Force retranslate selected items"""
        count = 0
        for obj in queryset:
            success = perform_translation(obj, 'Article')
            if success:
                count += 1

        self.message_user(request, f'{count} articles translated successfully')


class TerpeneAdmin(TranslatedModelAdmin):
    form = TerpeneAdminForm
    list_display = ('name', 'translation_status_badge', 'last_translated_at')
    search_fields = ('name',)  # name is NOT translated (Limonene, Myrcene, etc.)
    actions = ['force_retranslate']

    @admin.action(description='Force retranslate selected items')
    def force_retranslate(self, request, queryset):
        """Force retranslate selected items"""
        count = 0
        for obj in queryset:
            success = perform_translation(obj, 'Terpene')
            if success:
                count += 1

        self.message_user(request, f'{count} terpenes translated successfully')


# Simple admin for translated taxonomy models
class TaxonomyAdmin(TranslationAdmin):
    list_display = ('name_display',)
    search_fields = ('name_en', 'name_es')

    def name_display(self, obj):
        """Display name with both languages when available"""
        en = getattr(obj, 'name_en', None) or ''
        es = getattr(obj, 'name_es', None) or ''

        if en and es:
            return f'🇬🇧 {en} / 🇪🇸 {es}'
        elif en:
            return f'🇬🇧 {en}'
        elif es:
            return f'🇪🇸 {es}'
        return '-'
    name_display.short_description = 'Name'


admin.site.register(Strain, StrainAdmin)
admin.site.register(Article, ArticleAdmin)
admin.site.register(Terpene, TerpeneAdmin)
admin.site.register(ArticleCategory)
admin.site.register(Feeling, TaxonomyAdmin)
admin.site.register(Negative, TaxonomyAdmin)
admin.site.register(HelpsWith, TaxonomyAdmin)
admin.site.register(Flavor, TaxonomyAdmin)
