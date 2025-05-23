from django.contrib import admin
from .models import TenantPaymentModel

class TenantPaymentAdmin(admin.ModelAdmin):
    list_display = ('country','tenant', 'amount', 'transaction_id', 'status', 'paid_at', 'is_active', 'is_deleted')
    search_fields = ('tenant__id', 'transaction_id', 'status')
    list_filter = ('status', 'is_active', 'is_deleted')

admin.site.register(TenantPaymentModel, TenantPaymentAdmin)
