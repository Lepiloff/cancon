from django.contrib import admin
from .models import (
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


class StrainAdmin(admin.ModelAdmin):
    list_display = (
        'name',
        'category',
        'rating',
        'thc',
        'cbd',
        'cbg',
        'active',
        'main',
        'top',
        'is_review'
    )
    search_fields = ('name', 'category')
    list_filter = ('category', )
    filter_horizontal = ('feelings', 'negatives', 'helps_with', 'flavors')
    list_editable = ('active', 'main', 'top', 'is_review')


class ArticleImageInline(admin.TabularInline):
    model = ArticleImage
    extra = 1


class ArticleAdmin(admin.ModelAdmin):
    inlines = [ArticleImageInline]
    list_display = ('title',)
    search_fields = ('title', 'category')
    list_filter = ('category', )


class TerpeneAdmin(admin.ModelAdmin):
    list_display = ('name', 'description')
    search_fields = ('name',)
    list_filter = ('name',)


admin.site.register(Strain, StrainAdmin)
admin.site.register(ArticleCategory)
admin.site.register(Article, ArticleAdmin)
admin.site.register(Feeling)
admin.site.register(Negative)
admin.site.register(HelpsWith)
admin.site.register(Flavor)
admin.site.register(Terpene, TerpeneAdmin)
