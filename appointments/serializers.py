from rest_framework import serializers

class GetAppointmentsSerializer(serializers.Serializer):
    tenant_id = serializers.IntegerField(required=False)
    landlord_id = serializers.IntegerField(required=False)
