# notifications/urls.py

from django.urls import path
from .views import (
    register_tenant_device,
    register_landlord_device,
    toggle_tenant_notification,
    list_tenant_notifications,
    toggle_landlord_notification,
    list_landlord_notifications,
)

urlpatterns = [
    # Device registration
    path(
        'register_tenant_device/',
        register_tenant_device,
        name='tenant-device-register'
    ),
    path(
        'register_landlord_device/',
        register_landlord_device,
        name='landlord-device-register'
    ),

    # Tenant notification settings
    path(
        'list_tenant_notifications/',
        list_tenant_notifications,
        name='tenant-notifications-list'
    ),
    path(
        'toggle_tenant_notification/',
        toggle_tenant_notification,
        name='tenant-notifications-toggle'
    ),

    # Landlord notification settings
    path(
        'list_landlord_notifications/',
        list_landlord_notifications,
        name='landlord-notifications-list'
    ),
    path(
        'toggle_landlord_notification/',
        toggle_landlord_notification,
        name='landlord-notifications-toggle'
    ),
]
