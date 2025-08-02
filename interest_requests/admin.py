from django.contrib import admin
from .models import InterestRequestStatusModel, TenantInterestRequestModel, LandlordInterestRequestModel
from parler.admin import TranslatableAdmin
@admin.register(InterestRequestStatusModel)
class InterestRequestStatusAdmin(TranslatableAdmin):  # <--- Use this!
    list_display = ('code', 'get_label')

    def get_label(self, obj):
        return obj.safe_translation_getter('label', any_language=True)
    get_label.short_description = 'Label'
    
@admin.register(TenantInterestRequestModel)
class TenantInterestRequestAdmin(admin.ModelAdmin):
    list_display = ('tenant', 'bed', 'created_at', 'updated_at')
    list_filter = ( 'is_active', 'is_deleted')
    search_fields = ('tenant__email', 'bed__bed_number')
    ordering = ('-created_at',)

@admin.register(LandlordInterestRequestModel)
class LandlordInterestRequestAdmin(admin.ModelAdmin):
    list_display = ('bed', 'tenant', 'status', 'created_at', 'updated_at')
    list_filter = ('is_active', 'is_deleted')
    search_fields = ('tenant__email', 'bed__bed_number', 'bed__room__property__landlord__first_name')
    ordering = ('-created_at',)
