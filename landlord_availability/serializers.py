from django.forms import ValidationError
from rest_framework import serializers

class AddLandlordAvailabilitySerializer(serializers.Serializer):
    landlord_id = serializers.IntegerField(required=True)
    property_id = serializers.IntegerField(required=True)
    date = serializers.DateField(required=False)
    start_date = serializers.DateField(required=False)
    end_date = serializers.DateField(required=False)
    slot_id = serializers.IntegerField(required=False, allow_null=True)
    time_slots = serializers.ListField(
        child=serializers.DictField(child=serializers.CharField()),
        required=True
    )

    def validate(self, data):
        # must have either date or both start_date & end_date
        if not data.get('date') and not (data.get('start_date') and data.get('end_date')):
            raise serializers.ValidationError("Provide either 'date' or both 'start_date' and 'end_date'.")
        return data

# ——————————————————————————————————————————————————————————————————————
# NEW: serializer for fetching dates
class GetLandlordAvailabilityDatesSerializer(serializers.Serializer):
    landlord_id = serializers.IntegerField(required=True)
    property_id = serializers.IntegerField(required=True)
    month       = serializers.IntegerField(required=False)

# NEW: serializer for fetching slots
class GetLandlordAvailabilitySlotsSerializer(serializers.Serializer):
    landlord_id = serializers.IntegerField(required=True)
    property_id = serializers.IntegerField(required=True)
    date        = serializers.DateField(required=False)
# ——————————————————————————————————————————————————————————————————————



class DeleteLandlordAvailabilitySlotSerializer(serializers.Serializer):
    slot_id  = serializers.IntegerField(required=False)
    slot_ids = serializers.ListField(
        child=serializers.IntegerField(), required=False
    )

    def validate(self, data):
        if not data.get('slot_id') and not data.get('slot_ids'):
            raise serializers.ValidationError(
                "You must provide either `slot_id` or `slot_ids`."
            )
        return data