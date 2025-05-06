from rest_framework import serializers

class GetAppointmentsSerializer(serializers.Serializer):
    tenant_id = serializers.IntegerField(required=False)
    landlord_id = serializers.IntegerField(required=False)
    property_id = serializers.IntegerField(required=False)
    status = serializers.CharField(
        required=False,
        allow_blank=True,    # <- allow "" (empty) without errors
        allow_null=True,     # <- if you ever pass explicit null
    )
class BedActionSerializer(serializers.Serializer):
    bed_id = serializers.IntegerField()
    tenant_id = serializers.IntegerField(required=False)
    slot_id = serializers.IntegerField(required=False)
    appointment_id = serializers.IntegerField(required=False)

class BookAppointmentSerializer(serializers.Serializer):
    tenant_id   = serializers.IntegerField()
    landlord_id = serializers.IntegerField()
    bed_id      = serializers.IntegerField()
    slot_id     = serializers.IntegerField()