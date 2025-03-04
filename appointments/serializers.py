from rest_framework import serializers

class GetAppointmentsSerializer(serializers.Serializer):
    tenant_id = serializers.IntegerField(required=True)