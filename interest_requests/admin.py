from django.contrib import admin
from .models import TenantInterestRequestModel, LandlordInterestRequestModel

@admin.register(TenantInterestRequestModel)
class TenantInterestRequestAdmin(admin.ModelAdmin):
    list_display = ('tenant', 'bed', 'status', 'created_at', 'updated_at')
    list_filter = ('status', 'is_active', 'is_deleted')
    search_fields = ('tenant__email', 'bed__bed_number')
    ordering = ('-created_at',)

@admin.register(LandlordInterestRequestModel)
class LandlordInterestRequestAdmin(admin.ModelAdmin):
    list_display = ('bed', 'tenant', 'status', 'created_at', 'updated_at')
    list_filter = ('status', 'is_active', 'is_deleted')
    search_fields = ('tenant__email', 'bed__bed_number', 'bed__room__property__landlord__first_name')
    ordering = ('-created_at',)
