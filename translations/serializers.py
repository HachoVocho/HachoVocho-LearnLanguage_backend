from rest_framework import serializers

from landlord.models import LandlordDetailsModel
from tenant.models import TenantDetailsModel
from .models import TranslationModel, LanguageModel

class TranslationSerializer(serializers.ModelSerializer):
    # Accept language_code from the request payload.
    language_code = serializers.CharField(write_only=True)

    class Meta:
        model = TranslationModel
        fields = ('id', 'key', 'language_code', 'value')

    def validate_language_code(self, value):
        if not LanguageModel.objects.filter(code=value).exists():
            raise serializers.ValidationError("Language code does not exist.")
        return value

    def create(self, validated_data):
        # Retrieve the language instance using the provided language_code.
        lang_code = validated_data.pop('language_code')
        language = LanguageModel.objects.get(code=lang_code)
        validated_data['language'] = language
        return TranslationModel.objects.create(**validated_data)


class TranslationListSerializer(serializers.ModelSerializer):
    class Meta:
        model = TranslationModel
        fields = ('id', 'key', 'value')


class LanguageSerializer(serializers.ModelSerializer):
    class Meta:
        model = LanguageModel
        fields = ('id', 'code', 'name')

class TenantLanguageUpdateSerializer(serializers.Serializer):
    tenant_id = serializers.IntegerField()
    language_code = serializers.CharField(max_length=10)

    def validate_tenant_id(self, value):
        if not TenantDetailsModel.objects.filter(id=value).exists():
            raise serializers.ValidationError(f"Tenant with id {value} does not exist.")
        return value

    def validate_language_code(self, value):
        if not LanguageModel.objects.filter(code=value).exists():
            raise serializers.ValidationError(f"Language code '{value}' does not exist.")
        return value

class LandlordLanguageUpdateSerializer(serializers.Serializer):
    landlord_id = serializers.IntegerField()
    language_code = serializers.CharField(max_length=10)

    def validate_tenant_id(self, value):
        if not LandlordDetailsModel.objects.filter(id=value).exists():
            raise serializers.ValidationError(f"Tenant with id {value} does not exist.")
        return value

    def validate_language_code(self, value):
        if not LanguageModel.objects.filter(code=value).exists():
            raise serializers.ValidationError(f"Language code '{value}' does not exist.")
        return value