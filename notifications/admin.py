# help_support/admin.py

from django.contrib import admin
from .models import TenantDeviceNotificationModel, LandlordDeviceNotificationModel
from django.contrib import admin
from .models import (
    NotificationTypeModel,
    TenantNotificationSettingModel,
    LandlordNotificationSettingModel,
)

@admin.register(TenantDeviceNotificationModel)
class TenantDeviceNotificationAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "tenant",
        "player_id",
        "is_active",
        "is_deleted",
        "created_at",
        "updated_at",
    )
    list_filter = ("is_active", "is_deleted", "created_at")
    search_fields = ("tenant__email", "tenant__first_name", "tenant__last_name", "player_id")
    readonly_fields = ("created_at", "updated_at")


@admin.register(LandlordDeviceNotificationModel)
class LandlordDeviceNotificationAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "landlord",
        "player_id",
        "is_active",
        "is_deleted",
        "created_at",
        "updated_at",
    )
    list_filter = ("is_active", "is_deleted", "created_at")
    search_fields = ("landlord__email", "landlord__first_name", "landlord__last_name", "player_id")
    readonly_fields = ("created_at", "updated_at")


@admin.register(NotificationTypeModel)
class NotificationTypeAdmin(admin.ModelAdmin):
    list_display = ('id','code', 'name', 'description')
    search_fields = ('code', 'name')


@admin.register(TenantNotificationSettingModel)
class TenantNotificationSettingAdmin(admin.ModelAdmin):
    list_display = ('id','tenant', 'notification_type', 'is_enabled', 'updated_at')
    list_filter = ('notification_type', 'is_enabled')
    search_fields = ('tenant__user__username', 'notification_type__code')
    raw_id_fields = ('tenant', 'notification_type')


@admin.register(LandlordNotificationSettingModel)
class LandlordNotificationSettingAdmin(admin.ModelAdmin):
    list_display = ('id','landlord', 'notification_type', 'is_enabled', 'updated_at')
    list_filter = ('notification_type', 'is_enabled')
    search_fields = ('landlord__user__username', 'notification_type__code')
    raw_id_fields = ('landlord', 'notification_type')
