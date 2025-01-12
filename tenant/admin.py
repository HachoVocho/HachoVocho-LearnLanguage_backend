from django.contrib import admin
from .models import TenantDetailsModel

@admin.register(TenantDetailsModel)
class TenantDetailsAdmin(admin.ModelAdmin):
    """
    Custom admin class to manage tenant users.
    """
    list_display = ('first_name', 'last_name', 'email', 'is_active', 'created_at')  # Columns displayed in admin
    search_fields = ('email', 'first_name', 'last_name')  # Search functionality
    list_filter = ('is_active', 'is_deleted')  # Filters for the sidebar
    readonly_fields = ('created_at', 'deleted_at')  # Fields that are read-only

