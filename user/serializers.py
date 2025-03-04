from rest_framework import serializers

class UserRoleSerializer(serializers.Serializer):
    role_name = serializers.CharField(max_length=20)
    description = serializers.CharField(max_length=50)

class EmailVerificationSerializer(serializers.Serializer):
    email = serializers.EmailField()
    otp = serializers.CharField(max_length=6)
    player_id = serializers.CharField(max_length=60)

class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

class ForgotPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField()

class PasswordUpdateSerializer(serializers.Serializer):
    email = serializers.EmailField()
    new_password = serializers.CharField(min_length=8, write_only=True)
