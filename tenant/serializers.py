from django.contrib.auth.hashers import make_password
from rest_framework import serializers
from .models import TenantDetailsModel, TenantEmailVerificationModel
from django.core.mail import send_mail
from django.utils.timezone import now
import random

class TenantSignupSerializer(serializers.ModelSerializer):
    class Meta:
        model = TenantDetailsModel
        fields = ['first_name', 'last_name', 'email', 'password']
        extra_kwargs = {
            'password': {'write_only': True}  # Password should not be readable
        }

    def create(self, validated_data):
        """
        Overriding create method to hash the password, create an OTP, and send a verification email.
        """
        validated_data['password'] = make_password(validated_data['password'])
        tenant = TenantDetailsModel.objects.create(**validated_data)

        # Generate OTP
        otp = str(random.randint(100000, 999999))  # 6-digit OTP
        TenantEmailVerificationModel.objects.create(
            tenant=tenant,
            otp=otp,
            is_verified=False,
            created_at=now()
        )

        # Send OTP email
        try:
            send_mail(
                subject='Verify Your Email',
                message=f'Your OTP for email verification is: {otp}',
                from_email=None,  # Uses DEFAULT_FROM_EMAIL in settings.py
                recipient_list=[tenant.email],
                fail_silently=False,  # Raise error if email fails
            )
        except Exception as e:
            raise serializers.ValidationError(f"Failed to send email: {str(e)}")

        return tenant
