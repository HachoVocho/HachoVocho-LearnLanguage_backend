# help_support/serializers.py
from rest_framework import serializers
from .models import STATUS_CHOICES

class TenantTicketCreateSerializer(serializers.Serializer):
    tenant_id   = serializers.IntegerField()
    description = serializers.CharField()

class LandlordTicketCreateSerializer(serializers.Serializer):
    landlord_id = serializers.IntegerField()
    description = serializers.CharField()

class AdminTicketUpdateSerializer(serializers.Serializer):
    ticket_type   = serializers.ChoiceField(choices=['tenant','landlord'])
    ticket_id     = serializers.IntegerField()
    admin_comment = serializers.CharField()
    status        = serializers.ChoiceField(choices=[c[0] for c in STATUS_CHOICES])

class UserTicketCloseSerializer(serializers.Serializer):
    ticket_type = serializers.ChoiceField(choices=['tenant','landlord'])
    ticket_id   = serializers.IntegerField()

class TicketListParamsSerializer(serializers.Serializer):
    ticket_type = serializers.ChoiceField(choices=['tenant','landlord'])
    user_id     = serializers.IntegerField()
