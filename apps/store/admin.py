from django.contrib import admin
from .models import Vendor, Store, Location


@admin.register(Vendor)
class VendorAdmin(admin.ModelAdmin):
    list_display = ('name', 'address', 'contact_email', 'contact_phone')
    search_fields = ('name', 'address')


@admin.register(Location)
class LocationAdmin(admin.ModelAdmin):
    list_display = ('address', 'latitude', 'longitude', 'country')
    search_fields = ('address', 'country')


@admin.register(Store)
class StoreAdmin(admin.ModelAdmin):
    list_display = (
        'name',
        'vendor',
        'location',
    )
    search_fields = ('name', 'vendor__name', 'location__address')
    list_filter = ('vendor', 'location')
    raw_id_fields = ('vendor', 'location')
