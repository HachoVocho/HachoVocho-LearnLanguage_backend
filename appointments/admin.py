from django.contrib import admin
from .models import AppointmentBookingModel

@admin.register(AppointmentBookingModel)
class AppointmentBookingAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'tenant',
        'landlord',
        'bed',
        'time_slot',
        'status',
        'created_at'
    )
    list_filter = ('status', 'is_active', 'is_deleted', 'created_at')
    search_fields = (
        'tenant__first_name', 
        'tenant__last_name', 
        'landlord__first_name', 
        'landlord__last_name',
        'bed__id',
        'time_slot__id'
    )
    ordering = ('-created_at',)
    readonly_fields = ('created_at', 'updated_at')
