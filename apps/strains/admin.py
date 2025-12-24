from django import forms
from django.contrib import admin, messages
from django.urls import path
from django.shortcuts import render
from django.utils import timezone
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
from apps.strains.leafly_import import LeaflyCopywriter, CopywritingError
from apps.strains.signals import perform_translation
from apps.translation import OpenAITranslator
from apps.translation.base_translator import TranslationError


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


class StrainCopywriterForm(forms.Form):
    strain = forms.ModelChoiceField(
        queryset=Strain.objects.order_by('name'),
        required=False,
        label='Strain (optional)',
    )
    source_text = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 8, 'style': 'width: 100%;'}),
        label='Source text',
        help_text='Paste raw text from any site (links will be removed).',
    )
    generated_text_en = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'rows': 8, 'style': 'width: 100%;'}),
        label='Generated text (EN)',
    )
    generated_text_es = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'rows': 8, 'style': 'width: 100%;'}),
        label='Generated text (ES)',
    )
    confirm_overwrite = forms.BooleanField(
        required=False,
        label='Confirm overwrite',
        help_text='Check to overwrite the selected strain text.',
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['generated_text_en'].widget.attrs['readonly'] = True
        self.fields['generated_text_es'].widget.attrs['readonly'] = True


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
    change_list_template = 'admin/strains/strain/change_list.html'
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

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                'copywriter/',
                self.admin_site.admin_view(self.copywriter_view),
                name='strains_strain_copywriter',
            ),
        ]
        return custom_urls + urls

    def copywriter_view(self, request):
        form = StrainCopywriterForm()
        if request.method == 'POST':
            action = request.POST.get('action')
            form = StrainCopywriterForm(request.POST)

            if not form.is_valid():
                self.message_user(
                    request,
                    'Please correct the errors below.',
                    level=messages.ERROR,
                )
            else:
                strain = form.cleaned_data['strain']
                source_text = form.cleaned_data['source_text']
                generated_en = (form.cleaned_data.get('generated_text_en') or '').strip()
                generated_es = (form.cleaned_data.get('generated_text_es') or '').strip()

                if action == 'generate':
                    try:
                        copywriter = LeaflyCopywriter()
                        generated_en = copywriter.rewrite_raw_text(
                            source_text,
                            strain_name=strain.name if strain else None,
                        )
                        translator = OpenAITranslator()
                        translations = translator.translate(
                            'Strain',
                            {'text_content': generated_en},
                            'en',
                            'es',
                        )
                        generated_es = (translations.get('text_content') or '').strip()
                        if not generated_es:
                            raise TranslationError('Translation returned empty text_content')

                        form = StrainCopywriterForm(initial={
                            'strain': strain.id if strain else None,
                            'source_text': source_text,
                            'generated_text_en': generated_en,
                            'generated_text_es': generated_es,
                        })
                    except (CopywritingError, TranslationError, ValueError) as exc:
                        self.message_user(request, f'Generation failed: {exc}', level=messages.ERROR)

                elif action == 'apply':
                    if not strain:
                        form.add_error('strain', 'Select a strain to overwrite.')
                    if not form.cleaned_data.get('confirm_overwrite'):
                        form.add_error('confirm_overwrite', 'Confirmation is required.')
                    if not generated_en or not generated_es:
                        form.add_error(None, 'Generate text first before applying.')

                    if not form.errors:
                        strain.text_content = generated_en
                        strain.text_content_en = generated_en
                        strain.text_content_es = generated_es
                        strain.translation_status = 'synced'
                        strain.translation_error = None
                        strain.last_translated_at = timezone.now()
                        strain.translation_source_hash = strain.get_translatable_content_hash()
                        strain._skip_translation_check = True
                        strain.save(update_fields=[
                            'text_content',
                            'text_content_en',
                            'text_content_es',
                            'translation_status',
                            'translation_error',
                            'last_translated_at',
                            'translation_source_hash',
                            'updated_at',
                        ])
                        self.message_user(
                            request,
                            f'Text updated for {strain.name}.',
                            level=messages.SUCCESS,
                        )

                else:
                    self.message_user(
                        request,
                        'Unknown action. Use Generate or Apply.',
                        level=messages.ERROR,
                    )

        context = {
            **self.admin_site.each_context(request),
            'form': form,
            'title': 'Strain Copywriter',
        }
        return render(request, 'admin/strains/strain/copywriter.html', context)

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
