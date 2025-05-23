from rest_framework_simplejwt.serializers import TokenRefreshSerializer
from rest_framework_simplejwt.exceptions import TokenError
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
    isLandlord = serializers.BooleanField(required=False, default=False)

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
    
class NoUserLookupTokenRefreshSerializer(TokenRefreshSerializer):
    """
    Exactly like TokenRefreshSerializer, but we skip any user lookup.
    We simply validate the refresh, and return a fresh access.
    """
    def validate(self, attrs):
        # This is almost identical to the parent, except we never do token.user
        try:
            refresh = self.token_class(attrs['refresh'])
        except TokenError as e:
            raise e

        data = {"access": str(refresh.access_token)}
        # We re-use the incoming refresh, so put it back on the response
        data["refresh"] = attrs["refresh"]
        print(f'datanewsvds {data}')
        return data