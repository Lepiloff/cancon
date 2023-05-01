from django.contrib import admin
from .models import Strain, Feeling, Negative, HelpsWith, Flavor


class StrainAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'rating', 'thc', 'cbd', 'cbg', 'active')
    search_fields = ('name', 'category')
    list_filter = ('category', )
    filter_horizontal = ('feelings', 'negatives', 'helps_with', 'flavors')
    list_editable = ('active',)


admin.site.register(Strain, StrainAdmin)
admin.site.register(Feeling)
admin.site.register(Negative)
admin.site.register(HelpsWith)
admin.site.register(Flavor)
