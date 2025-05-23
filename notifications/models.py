from django.db import models
from django.utils.timezone import now
from tenant.models import TenantDetailsModel
from landlord.models import LandlordDetailsModel

class TenantDeviceNotificationModel(models.Model):
    tenant   = models.ForeignKey(
                  TenantDetailsModel,
                  on_delete=models.CASCADE,
                  related_name="device_notifications"
               )
    player_id = models.CharField(
                  max_length=255,
                  unique=True
               )
    is_active  = models.BooleanField(default=True)
    is_deleted = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=now)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Tenant {self.tenant.id} → {self.player_id}"


class LandlordDeviceNotificationModel(models.Model):
    landlord  = models.ForeignKey(
                  LandlordDetailsModel,
                  on_delete=models.CASCADE,
                  related_name="device_notifications"
               )
    player_id = models.CharField(
                  max_length=255,
                  unique=True
               )
    is_active  = models.BooleanField(default=True)
    is_deleted = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=now)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Landlord {self.landlord.id} → {self.player_id}"

class NotificationTypeModel(models.Model):
    """
    Master list of all possible notification channels/events.
    """
    code = models.CharField(
        max_length=50,
        unique=True,
        help_text="Machine‐readable code, e.g. 'tenant_request', 'chat_message'"
    )
    name = models.CharField(max_length=100, help_text="Human‐readable name")
    description = models.TextField(blank=True)

    def __str__(self):
        return self.name


class TenantNotificationSettingModel(models.Model):
    """
    Each tenant has one setting per NotificationType.
    """
    tenant = models.ForeignKey(
        TenantDetailsModel,
        on_delete=models.CASCADE,
        related_name="notification_settings"
    )
    notification_type = models.ForeignKey(
        NotificationTypeModel,
        on_delete=models.CASCADE,
        related_name="tenant_settings"
    )
    is_enabled = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("tenant", "notification_type")

    def __str__(self):
        status = "On" if self.is_enabled else "Off"
        return f"Tenant {self.tenant.id} – {self.notification_type.code}: {status}"


class LandlordNotificationSettingModel(models.Model):
    """
    Each landlord has one setting per NotificationType.
    """
    landlord = models.ForeignKey(
        LandlordDetailsModel,
        on_delete=models.CASCADE,
        related_name="notification_settings"
    )
    notification_type = models.ForeignKey(
        NotificationTypeModel,
        on_delete=models.CASCADE,
        related_name="landlord_settings"
    )
    is_enabled = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("landlord", "notification_type")

    def __str__(self):
        status = "On" if self.is_enabled else "Off"
        return f"Landlord {self.landlord.id} – {self.notification_type.code}: {status}"
