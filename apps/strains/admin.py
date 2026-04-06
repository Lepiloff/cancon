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
    FavoriteStrain,
    Strain,
    Feeling,
    Negative,
    HelpsWith,
    Flavor,
    Terpene,
)
from apps.strains.copywriter import (
    CopywritingError,
    get_copywriter_for_content_type,
    get_handler,
)
from apps.strains.llm_output import clean_generated_output
from apps.strains.signals import perform_translation
from apps.translation import get_translator
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


class CopywriterForm(forms.Form):
    """Generic copywriter form, parameterized by content type."""

    target_object = forms.ModelChoiceField(
        queryset=Strain.objects.none(),
        required=False,
        label='Target (optional)',
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
        help_text='Check to overwrite the selected object text.',
    )

    def __init__(self, *args, content_type='strain', **kwargs):
        super().__init__(*args, **kwargs)
        handler = get_handler(content_type)
        model_class = handler['_model_class']
        self.fields['target_object'].queryset = model_class.objects.order_by(
            handler['queryset_order']
        )
        self.fields['target_object'].label = f'{handler["label"]} (optional)'
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


class CopywriterAdminMixin:
    """Mixin that adds a copywriter view to any TranslatedModelAdmin."""

    copywriter_content_type = None  # Set in subclass: 'strain', 'terpene', 'article'

    def get_urls(self):
        urls = super().get_urls()
        if self.copywriter_content_type:
            custom_urls = [
                path(
                    'copywriter/',
                    self.admin_site.admin_view(self.copywriter_view),
                    name=f'strains_{self.copywriter_content_type}_copywriter',
                ),
            ]
            return custom_urls + urls
        return urls

    def copywriter_view(self, request):
        ct = self.copywriter_content_type
        handler = get_handler(ct)
        form = CopywriterForm(content_type=ct)

        if request.method == 'POST':
            action = request.POST.get('action')
            form = CopywriterForm(request.POST, content_type=ct)

            if not form.is_valid():
                self.message_user(request, 'Please correct the errors below.', level=messages.ERROR)
            else:
                target_obj = form.cleaned_data['target_object']
                source_text = form.cleaned_data['source_text']
                generated_en = (form.cleaned_data.get('generated_text_en') or '').strip()
                generated_es = (form.cleaned_data.get('generated_text_es') or '').strip()

                if action == 'generate':
                    try:
                        copywriter = get_copywriter_for_content_type(ct)
                        result = copywriter.generate(source_text, obj=target_obj, content_type=ct)
                        generated_en = clean_generated_output(result.get(handler['output_key'], ''), ct)

                        translator = get_translator()
                        translations = translator.translate(
                            handler['translate_model_name'],
                            {handler['translate_field']: generated_en},
                            'en',
                            'es',
                        )
                        generated_es = clean_generated_output(
                            translations.get(handler['translate_field']) or '',
                            ct,
                        )
                        if not generated_es:
                            raise TranslationError('Translation returned empty text')

                        form = CopywriterForm(
                            initial={
                                'target_object': target_obj.id if target_obj else None,
                                'source_text': source_text,
                                'generated_text_en': generated_en,
                                'generated_text_es': generated_es,
                            },
                            content_type=ct,
                        )
                    except (CopywritingError, TranslationError, ValueError) as exc:
                        self.message_user(request, f'Generation failed: {exc}', level=messages.ERROR)

                elif action == 'apply':
                    if generated_en:
                        generated_en = clean_generated_output(generated_en, ct)
                    if generated_es:
                        generated_es = clean_generated_output(generated_es, ct)
                    if not target_obj:
                        form.add_error('target_object', f'Select a {handler["label"].lower()} to overwrite.')
                    if not form.cleaned_data.get('confirm_overwrite'):
                        form.add_error('confirm_overwrite', 'Confirmation is required.')
                    if not generated_en or not generated_es:
                        form.add_error(None, 'Generate text first before applying.')

                    if not form.errors:
                        target_field = handler['target_field']
                        en_field = f'{target_field}_en'
                        es_field = f'{target_field}_es'

                        setattr(target_obj, target_field, generated_en)
                        setattr(target_obj, en_field, generated_en)
                        setattr(target_obj, es_field, generated_es)
                        target_obj.translation_status = 'synced'
                        target_obj.translation_error = None
                        target_obj.last_translated_at = timezone.now()
                        target_obj.translation_source_hash = target_obj.get_translatable_content_hash()
                        target_obj._skip_translation_check = True

                        update_fields = [
                            target_field, en_field, es_field,
                            'translation_status', 'translation_error',
                            'last_translated_at', 'translation_source_hash',
                        ]
                        if hasattr(target_obj, 'updated_at'):
                            update_fields.append('updated_at')
                        target_obj.save(update_fields=update_fields)

                        obj_name = getattr(target_obj, handler['name_field'], str(target_obj))
                        self.message_user(
                            request,
                            f'Text updated for {obj_name}.',
                            level=messages.SUCCESS,
                        )
                else:
                    self.message_user(request, 'Unknown action.', level=messages.ERROR)

        context = {
            **self.admin_site.each_context(request),
            'form': form,
            'title': f'{handler["label"]} Copywriter',
            'content_type_label': handler['label'],
        }
        return render(request, 'admin/strains/copywriter.html', context)


class AlternativeNameInline(admin.TabularInline):
    model = AlternativeStrainName
    extra = 1


class StrainAdmin(CopywriterAdminMixin, TranslatedModelAdmin):
    form = StrainAdminForm
    copywriter_content_type = 'strain'
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
    filter_horizontal = ('feelings', 'negatives', 'helps_with', 'flavors', 'parents')
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


class ArticleAdmin(CopywriterAdminMixin, TranslatedModelAdmin):
    form = ArticleAdminForm
    copywriter_content_type = 'article'
    change_list_template = 'admin/strains/article/change_list.html'
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


class TerpeneAdmin(CopywriterAdminMixin, TranslatedModelAdmin):
    form = TerpeneAdminForm
    copywriter_content_type = 'terpene'
    change_list_template = 'admin/strains/terpene/change_list.html'
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
admin.site.register(FavoriteStrain)
