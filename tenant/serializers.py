from django.contrib.auth.hashers import make_password
from django.forms import ValidationError
from rest_framework import serializers

from landlord.models import LandlordDetailsModel
from localization.models import CityModel
from .models import TenantDetailsModel, TenantDocumentTypeModel, TenantEmailVerificationModel, TenantIdentityVerificationModel, TenantPreferenceAnswerModel, TenantPreferenceOptionModel, TenantPreferenceQuestionModel, TenantPreferenceQuestionTypeModel
from django.core.mail import send_mail
from django.utils.timezone import now
import random

class TenantSignupSerializer(serializers.ModelSerializer):
    first_name = serializers.CharField(max_length=50)
    last_name = serializers.CharField(max_length=50,
                                      required=False,  # Makes the field optional
        allow_blank=True
                                      )
    email = serializers.EmailField()
    password = serializers.CharField(
        max_length=128,
        write_only=True,
        style={'input_type': 'password'},
        allow_blank=True
    )

    class Meta:
        model = TenantDetailsModel
        fields = ['first_name', 'last_name', 'email', 'password']
        extra_kwargs = {
            'password': {'write_only': True}
        }

    def validate_password(self, value):
        # Allow empty password string without throwing an error.
        # Optionally, if not empty, you might want to check for a minimum length.
        if value != "" and len(value) < 6:
            raise serializers.ValidationError("Password must be at least 6 characters.")
        return value


# Serializer for Question Type (Single, Multiple, Priority)
class TenantQuestionTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = TenantPreferenceQuestionTypeModel
        fields = ['id', 'type_name', 'description']

# Serializer for Tenant Options (for priority-based and multiple select questions)
class TenantOptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = TenantPreferenceOptionModel
        fields = ['id', 'option_text']

# Serializer for Tenant Questions
class TenantQuestionSerializer(serializers.ModelSerializer):
    question_type = TenantQuestionTypeSerializer()
    question_options = TenantOptionSerializer(many=True, read_only=True)

    class Meta:
        model = TenantPreferenceQuestionModel
        fields = ['id', 'question_text', 'question_type', 'question_options']

class TenantPreferenceAnswerSerializer(serializers.Serializer):
    user_id = serializers.IntegerField()
    answers = serializers.ListField(
        child=serializers.DictField(
            child=serializers.JSONField()
        )
    )


class TenantPreferenceAnswerDetailSerializer(serializers.ModelSerializer):
    option_id = serializers.IntegerField(source='option.id')
    priority = serializers.IntegerField()

    class Meta:
        model = TenantPreferenceAnswerModel
        fields = ['option_id', 'priority']

class TenantPreferenceQuestionsAnswersRequestSerializer(serializers.Serializer):
    user_id = serializers.IntegerField()

class TenantProfileRequestSerializer(serializers.Serializer):
    user_id = serializers.IntegerField()

class TenantIdentityDocumentSerializer(serializers.ModelSerializer):
    files = serializers.SerializerMethodField()

    class Meta:
        model = TenantIdentityVerificationModel
        fields = [
            'id',
            'tenant',
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

class TenantDocumentTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = TenantDocumentTypeModel
        fields = ['id', 'type_name', 'description']

class AddIdentityDocumentSerializer(serializers.Serializer):
    tenant_id = serializers.IntegerField()
    document_type = serializers.IntegerField()
    document_number = serializers.CharField(max_length=100, allow_blank=True, required=False)

# In your serializers.py, add a new serializer for update:
class TenantIdentityDocumentUpdateSerializer(serializers.ModelSerializer):
    document_number = serializers.CharField(max_length=100, allow_blank=True, required=False)
    class Meta:
        model = TenantIdentityVerificationModel
        fields = '__all__'
    
    def validate_document_number(self, value):
        # For update, simply return the value without uniqueness check.
        return value

class PropertyListRequestSerializer(serializers.Serializer):
    tenant_id = serializers.IntegerField(
        min_value=1,
        required=True,
        help_text="ID of the tenant"
    )
    city_id = serializers.IntegerField(
        min_value=-1,
        required=True,
        help_text="ID of the preferred city"
    )

    
class PropertyDetailRequestSerializer(serializers.Serializer):
    property_id = serializers.IntegerField(required=True)
    tenant_id = serializers.IntegerField(required=True)
    