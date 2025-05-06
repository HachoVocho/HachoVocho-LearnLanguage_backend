from rest_framework import serializers

class AddLandlordAvailabilitySerializer(serializers.Serializer):
    landlord_id = serializers.IntegerField(required=True)
    property_id = serializers.IntegerField(required=True)
    date = serializers.DateField(required=True)
    time_slots = serializers.ListField(
        child=serializers.DictField(
            child=serializers.CharField()
        ), required=True
    )

class GetLandlordAvailabilitySerializer(serializers.Serializer):
    landlord_id = serializers.IntegerField(required=True)
    property_id = serializers.IntegerField(required=True)
    month = serializers.IntegerField(required=False)


class GetLandlordAvailabilityByBedSerializer(serializers.Serializer):
    landlord_id = serializers.IntegerField(required=False)
    property_id = serializers.IntegerField(required=False)
    bed_id = serializers.IntegerField(required=False)