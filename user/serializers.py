from rest_framework import serializers
from .models import UserRoleModel
from tenant.models import TenantEmailVerificationModel
from landlord.models import LandlordEmailVerificationModel
from django.utils.timezone import now, timedelta

class UserRoleSerializer(serializers.Serializer):
    role_name = serializers.CharField(max_length=20)
    description = serializers.CharField(max_length=50)


class EmailVerificationSerializer(serializers.Serializer):
    email = serializers.EmailField()
    otp = serializers.CharField(max_length=6)

    def validate(self, data):
        """
        Validate OTP and email for both tenant and landlord.
        """
        email = data['email']
        otp = data['otp']

        # Check for Tenant
        try:
            tenant_verification = TenantEmailVerificationModel.objects.get(
                tenant__email=email,
                otp=otp,
                is_verified=False
            )
            # Check OTP expiration
            if now() > tenant_verification.created_at + timedelta(minutes=15):
                raise serializers.ValidationError("OTP has expired.")
            data['user_type'] = 'tenant'
            data['verification_entry'] = tenant_verification
            return data
        except TenantEmailVerificationModel.DoesNotExist:
            pass

        # Check for Landlord
        try:
            landlord_verification = LandlordEmailVerificationModel.objects.get(
                landlord__email=email,
                otp=otp,
                is_verified=False
            )
            # Check OTP expiration
            if now() > landlord_verification.created_at + timedelta(minutes=15):
                raise serializers.ValidationError("OTP has expired.")
            data['user_type'] = 'landlord'
            data['verification_entry'] = landlord_verification
            return data
        except LandlordEmailVerificationModel.DoesNotExist:
            pass

        # If no match found
        raise serializers.ValidationError("Invalid email or OTP.")

    def save(self):
        """
        Mark the OTP as verified and invalidate it.
        """
        verification_entry = self.validated_data['verification_entry']
        verification_entry.is_verified = True
        verification_entry.verified_at = now()
        verification_entry.save()