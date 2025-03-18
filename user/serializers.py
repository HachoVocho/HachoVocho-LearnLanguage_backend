from rest_framework import serializers

class UserRoleSerializer(serializers.Serializer):
    role_name = serializers.CharField(max_length=20)
    description = serializers.CharField(max_length=50)

class EmailVerificationSerializer(serializers.Serializer):
    email = serializers.EmailField()
    otp = serializers.CharField(max_length=6)
    player_id = serializers.CharField(max_length=60,required=False,allow_blank=True)

class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, allow_blank=True)

class ForgotPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField()

class PasswordUpdateSerializer(serializers.Serializer):
    email = serializers.EmailField()
    new_password = serializers.CharField(min_length=8, write_only=True)

class OTPSendSerializer(serializers.Serializer):
    phone_number = serializers.CharField(max_length=15)
    user_id = serializers.CharField()  # You can also use IntegerField if user_id is numeric
    role_name = serializers.ChoiceField(choices=[('tenant', 'Tenant'), ('landlord', 'Landlord')])

class OTPVerifySerializer(serializers.Serializer):
    phone_number = serializers.CharField(max_length=15)
    user_id = serializers.CharField()
    role_name = serializers.ChoiceField(choices=[('tenant', 'Tenant'), ('landlord', 'Landlord')])
    otp = serializers.CharField(max_length=6)