from rest_framework import serializers
from .models import UserRoleModel
from tenant.models import TenantEmailVerificationModel
from django.utils.timezone import now, timedelta

class UserRoleSerializer(serializers.Serializer):
    role_name = serializers.CharField(max_length=20)
    description = serializers.CharField(max_length=50)


class EmailVerificationSerializer(serializers.Serializer):
    email = serializers.EmailField()
    otp = serializers.CharField(max_length=6)

    def validate(self, data):
        """
        Validate OTP and email.
        """
        try:
            verification_entry = TenantEmailVerificationModel.objects.get(
                tenant__email=data['email'],
                otp=data['otp'],
                is_verified=False
            )
        except TenantEmailVerificationModel.DoesNotExist:
            raise serializers.ValidationError("Invalid email or OTP.")

        # Check if the OTP has expired
        if now() > verification_entry.created_at + timedelta(minutes=15):
            raise serializers.ValidationError("OTP has expired.")

        return data

    def save(self):
        """
        Mark the OTP as verified and invalidate it.
        """
        data = self.validated_data
        verification_entry = TenantEmailVerificationModel.objects.get(
            tenant__email=data['email'],
            otp=data['otp']
        )
        verification_entry.is_verified = True
        verification_entry.verified_at = now()
        verification_entry.save()
