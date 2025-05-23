from django.contrib import admin
from .models import TenantSupportTicket, LandlordSupportTicket

@admin.register(TenantSupportTicket)
class TenantSupportTicketAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'tenant',
        'status',
        'updated_by',
        'created_at',
        'updated_at',
    )
    list_filter = ('status', 'updated_by', 'created_at')
    search_fields = ('tenant__user__email', 'description', 'admin_comment')
    readonly_fields = ('created_at', 'updated_at')
    ordering = ('-created_at',)


@admin.register(LandlordSupportTicket)
class LandlordSupportTicketAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'landlord',
        'status',
        'updated_by',
        'created_at',
        'updated_at',
    )
    list_filter = ('status', 'updated_by', 'created_at')
    search_fields = ('landlord__user__email', 'description', 'admin_comment')
    readonly_fields = ('created_at', 'updated_at')
    ordering = ('-created_at',)
