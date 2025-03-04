from django.contrib import admin
from .models import LandlordAvailabilityModel, LandlordAvailabilitySlotModel

@admin.register(LandlordAvailabilityModel)
class LandlordAvailabilityAdmin(admin.ModelAdmin):
    list_display = ('landlord_id', 'property_id', 'date', 'is_active', 'created_at')
    list_filter = ('is_active', 'date', 'property')
    search_fields = ('landlord__name', 'property__property_name', 'date')
    ordering = ('-date',)
    list_per_page = 20

    fieldsets = (
        ('Availability Details', {
            'fields': ('landlord', 'property', 'date', 'is_active', 'is_deleted')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )
    readonly_fields = ('created_at', 'updated_at')


@admin.register(LandlordAvailabilitySlotModel)
class LandlordAvailabilitySlotAdmin(admin.ModelAdmin):
    list_display = ('availability', 'start_time', 'end_time', 'is_active')
    list_filter = ('is_active', 'availability__date')
    search_fields = ('availability__landlord__name', 'availability__property__property_name')
    ordering = ('availability__date', 'start_time')
    list_per_page = 20

    fieldsets = (
        ('Slot Details', {
            'fields': ('availability', 'start_time', 'end_time', 'is_active', 'is_deleted')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )
    readonly_fields = ('created_at', 'updated_at')
