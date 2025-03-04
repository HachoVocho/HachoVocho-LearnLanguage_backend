from django.contrib.auth.hashers import make_password
from rest_framework import serializers
from .models import LandlordAnswerModel, LandlordBedMediaModel, LandlordDetailsModel, LandlordDocumentTypeModel, LandlordEmailVerificationModel, LandlordIdentityVerificationModel, LandlordPropertyMediaModel, LandlordRoomMediaModel
from django.core.mail import send_mail
from django.utils.timezone import now
import random
from .models import (
    LandlordPropertyDetailsModel,
    LandlordPropertyRoomDetailsModel,
    LandlordRoomWiseBedModel,
)
class LandlordSignupSerializer(serializers.ModelSerializer):
    first_name = serializers.CharField(max_length=50)
    last_name = serializers.CharField(max_length=50)
    email = serializers.EmailField()
    password = serializers.CharField(max_length=128, write_only=True)
    class Meta:
        model = LandlordDetailsModel
        fields = ['first_name', 'last_name', 'email', 'password']
        extra_kwargs = {
            'password': {'write_only': True}  # Password should not be readable
        }

class LandlordQuestionRequestSerializer(serializers.Serializer):
    user_id = serializers.IntegerField(required=True)
    bed_id = serializers.IntegerField(required=True)

from rest_framework import serializers

class LandlordPreferenceAnswerSerializer(serializers.Serializer):
    user_id = serializers.IntegerField(required=True)
    answers = serializers.ListField(
        child=serializers.DictField(
            child=serializers.JSONField()
        ),
        required=True
    )

class LandlordPropertyDetailsSerializer(serializers.ModelSerializer):
    class Meta:
        model = LandlordPropertyDetailsModel
        fields = '__all__'

class ActivePropertyMediaListSerializer(serializers.ListSerializer):
    def to_representation(self, data):
        # Filter the queryset before serialization.
        data = data.filter(is_active=True, is_deleted=False)
        return super().to_representation(data)

class LandlordPropertyMediaSerializer(serializers.ModelSerializer):
    class Meta:
        model = LandlordPropertyMediaModel
        fields = ['id', 'file', 'media_type']
        list_serializer_class = ActivePropertyMediaListSerializer

class LandlordPropertyListSerializer(serializers.ModelSerializer):
    property_media = LandlordPropertyMediaSerializer(many=True, read_only=True)
    property_type_name = serializers.CharField(source="property_type.type_name", read_only=True)

    class Meta:
        model = LandlordPropertyDetailsModel
        fields = [
            'id', 'property_name', 'property_address', 'property_size', 
            'property_type_name', 'number_of_rooms', 'property_media','property_city','pin_code'
        ]

class LandlordRoomMediaSerializer(serializers.ModelSerializer):
    class Meta:
        model = LandlordRoomMediaModel
        fields = ['id', 'file', 'media_type']
        list_serializer_class = ActivePropertyMediaListSerializer

class LandlordBedMediaSerializer(serializers.ModelSerializer):
    class Meta:
        model = LandlordBedMediaModel
        fields = ['id', 'file', 'media_type']
        list_serializer_class = ActivePropertyMediaListSerializer

# Add this new serializer
class LandlordAnswerSerializer(serializers.ModelSerializer):
    question = serializers.SerializerMethodField()
    selected_option = serializers.SerializerMethodField()

    class Meta:
        model = LandlordAnswerModel
        fields = ['question', 'selected_option', 'preference']

    def get_question(self, obj):
        return {
            "id": obj.question.id,
            "text": obj.question.question_text
        }

    def get_selected_option(self, obj):
        if obj.selected_option:
            return {
                "id": obj.selected_option.id,
                "text": getattr(obj.selected_option, 'title', str(obj.selected_option))
            }
        return None
    

# Update the bed serializer to include answers
class LandlordRoomWiseBedSerializer(serializers.ModelSerializer):
    bed_media = LandlordBedMediaSerializer(many=True, read_only=True)
    tenant_preference_answers = LandlordAnswerSerializer(many=True, read_only=True)


    class Meta:
        model = LandlordRoomWiseBedModel
        fields = [
            'id', 'bed_number', 'is_available', 'rent_amount',
            'availability_start_date', 'min_agreement_duration_in_months','is_rent_monthly',
            'bed_media','tenant_preference_same_as','tenant_preference_answers','same_as_bed_id'
        ]

class LandlordPropertyRoomDetailsSerializer(serializers.ModelSerializer):
    room_media = LandlordRoomMediaSerializer(many=True, read_only=True)
    beds = LandlordRoomWiseBedSerializer(many=True, read_only=True)

    class Meta:
        model = LandlordPropertyRoomDetailsModel
        fields = [
            'id', 'room_size', 'room_type', 'number_of_beds', 
            'number_of_windows', 'max_people_allowed', 'floor', 
            'location_in_property', 'room_media', 'beds','same_as_room_id'
        ]

class LandlordPropertyDetailSerializer(serializers.ModelSerializer):
    property_media = LandlordPropertyMediaSerializer(many=True, read_only=True)
    rooms = LandlordPropertyRoomDetailsSerializer(many=True, read_only=True)
    
    class Meta:
        model = LandlordPropertyDetailsModel
        fields = [
            'id', 'property_name', 'property_address', 'property_size', 
            'property_type', 'number_of_rooms', 'floor', 'property_description', 
            'latitude', 'longitude', 'property_media', 'rooms','property_city','pin_code','amenities'
        ]

    def to_representation(self, instance):
        """Override to_representation to include property_types and amenities"""
        data = super().to_representation(instance)

        # Fetch additional data and add it to the response
        data['property_types'] = [
            {
                'id': property_type['id'],
                'type_name': property_type['type_name'],
                'description': property_type['description']
            }
            for property_type in self.context.get('property_types', [])
        ]

        data['all_amenities'] = [
            {
                'id': amenity['id'],
                'name': amenity['name'],
                'description': amenity['description']
            }
            for amenity in self.context.get('amenities', [])
        ]

        return data
    
class PropertyListRequestSerializer(serializers.Serializer):
    landlord_id = serializers.IntegerField(required=True)

class LandlordPropertyDetailRequestSerializer(serializers.Serializer):
    property_id = serializers.IntegerField(required=True)
    landlord_id = serializers.IntegerField(required=True)

class TenantInterestRequestSerializer(serializers.Serializer):
    bed_id = serializers.IntegerField(required=True)
    tenant_id = serializers.IntegerField(required=True)

class LandlordProfileRequestSerializer(serializers.Serializer):
    landlord_id = serializers.IntegerField(required=True)

class UpdateLandlordProfileSerializer(serializers.ModelSerializer):
    landlord_id = serializers.IntegerField(required=True)
    date_of_birth = serializers.DateField(required=False, allow_null=True)

    class Meta:
        model = LandlordDetailsModel
        fields = [
            "landlord_id",
            "phone_number",
            "date_of_birth",
            "profile_picture"
        ]

    def validate_landlord_id(self, value):
        if not LandlordDetailsModel.objects.filter(id=value, is_active=True, is_deleted=False).exists():
            raise serializers.ValidationError("Invalid landlord ID or landlord is not active.")
        return value
    

class LandlordIdentityDocumentSerializer(serializers.ModelSerializer):
    files = serializers.SerializerMethodField()

    class Meta:
        model = LandlordIdentityVerificationModel
        fields = [
            'id',
            'landlord',
            'document_type',
            'document_number',
            'files',
            'verification_status',
            'submitted_at',
            'verified_at',
            'rejection_reason'
        ]
        read_only_fields = ['id', 'verification_status', 'submitted_at', 'verified_at', 'rejection_reason']

    def get_files(self, obj):
        request = self.context.get('request')
        return [request.build_absolute_uri(f.file.url) for f in obj.files.all()]

class LandlordDocumentTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = LandlordDocumentTypeModel
        fields = ['id', 'type_name', 'description']

class AddIdentityDocumentSerializer(serializers.Serializer):
    landlord_id = serializers.IntegerField()
    document_type = serializers.IntegerField()
    document_number = serializers.CharField(max_length=100, allow_blank=True, required=False)

# In your serializers.py, add a new serializer for update:
class LandlordIdentityDocumentUpdateSerializer(serializers.ModelSerializer):
    document_number = serializers.CharField(max_length=100, allow_blank=True, required=False)
    class Meta:
        model = LandlordIdentityVerificationModel
        fields = '__all__'
    
    def validate_document_number(self, value):
        # For update, simply return the value without uniqueness check.
        return value