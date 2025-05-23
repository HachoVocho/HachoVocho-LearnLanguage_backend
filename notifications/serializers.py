# notifications/serializers.py
from rest_framework import serializers

class TenantDeviceRegistrationSerializer(serializers.Serializer):
    tenant_id = serializers.IntegerField()
    player_id = serializers.CharField(max_length=255)

class LandlordDeviceRegistrationSerializer(serializers.Serializer):
    landlord_id = serializers.IntegerField()
    player_id   = serializers.CharField(max_length=255)

class TenantNotificationToggleSerializer(serializers.Serializer):
    tenant_id             = serializers.IntegerField()
    notification_type_id  = serializers.IntegerField()
    is_enabled            = serializers.BooleanField()


class LandlordNotificationToggleSerializer(serializers.Serializer):
    landlord_id           = serializers.IntegerField()
    notification_type_id  = serializers.IntegerField()
    is_enabled            = serializers.BooleanField()


class TenantNotificationListSerializer(serializers.Serializer):
    tenant_id             = serializers.IntegerField()


class LandlordNotificationListSerializer(serializers.Serializer):
    landlord_id           = serializers.IntegerField()