from django.contrib import admin
from .models import DeviceNotificationModel

@admin.register(DeviceNotificationModel)
class DeviceNotificationAdmin(admin.ModelAdmin):
    list_display = ('user_id', 'player_id', 'is_active', 'is_deleted', 'created_at', 'updated_at')
    list_filter = ('is_active', 'is_deleted', 'created_at')
    search_fields = ('user_id', 'player_id')
    ordering = ('-created_at',)
    readonly_fields = ('created_at', 'updated_at')

    def has_add_permission(self, request):
        """Disable the add permission if needed."""
        return True  # Set to False if you want to disable adding records manually

    def has_delete_permission(self, request, obj=None):
        """Disable delete permission if needed."""
        return True  # Set to False if you want to prevent deletion

