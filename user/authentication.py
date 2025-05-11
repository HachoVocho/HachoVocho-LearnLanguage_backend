# authentication.py

from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken
from rest_framework.exceptions import AuthenticationFailed
from django.contrib.auth.hashers import make_password
from django.contrib.auth import get_user_model

from tenant.models import TenantDetailsModel
from landlord.models import LandlordDetailsModel

class EnhancedJWTValidation(JWTAuthentication):
    """
    Extends SimpleJWT to:
      - Route get_user(...) to TenantDetailsModel or LandlordDetailsModel based on user_type claim
      - Validate email, pw_hash, last_login via validate_token()
    """

    def get_user(self, validated_token):
        """
        Look up either TenantDetailsModel or LandlordDetailsModel based
        on the token’s user_type claim, falling back to the default User.
        """
        print(f'validated_tokensdvdv {validated_token}')
        user_id   = validated_token.get("user_id")
        user_type = (validated_token.get("user_type") or "").lower()
        print(f"[EnhancedJWT] get_user: user_id={user_id}, user_type={user_type}")

        if user_type == "tenant":
            try:
                user = TenantDetailsModel.objects.get(pk=user_id)
                print(f"[EnhancedJWT] Loaded TenantDetailsModel: {user}")
                return user
            except TenantDetailsModel.DoesNotExist:
                print(f"[EnhancedJWT] Tenant not found for id={user_id}")
                raise AuthenticationFailed("Tenant not found", code="user_not_found")

        if user_type == "landlord":
            try:
                user = LandlordDetailsModel.objects.get(pk=user_id)
                print(f"[EnhancedJWT] Loaded LandlordDetailsModel: {user}")
                return user
            except LandlordDetailsModel.DoesNotExist:
                print(f"[EnhancedJWT] Landlord not found for id={user_id}")
                raise AuthenticationFailed("Landlord not found", code="user_not_found")

    def validate_token(self, user, token):
        """
        Verify critical claims match database:
          1. email must match
          2. password hash fragment must match (empty for no-password accounts)
          3. last_login must match
        """
        print(f"[EnhancedJWT] validate_token for user={user}, token={token.payload}")

        # 1) Email check
        token_email = token.get('email')
        print(f"[EnhancedJWT] Token email={token_email}, User email={user.email}")
        if token_email != user.email:
            print("[EnhancedJWT] Email mismatch")
            raise AuthenticationFailed("Token email mismatch")

        # 2) Password-hash fragment
        stored_pw_fragment = token.get('pw_hash', '')
        if hasattr(user, 'has_usable_password') and user.has_usable_password():
            current_pw_fragment = make_password(user.password)[:15]
        else:
            current_pw_fragment = ''
        print(f"[EnhancedJWT] stored_pw_fragment={stored_pw_fragment}, current_pw_fragment={current_pw_fragment}")
        if stored_pw_fragment != current_pw_fragment:
            print("[EnhancedJWT] Password fragment mismatch")
            raise AuthenticationFailed(
                "Password changed / no longer valid—please re-login"
            )

        # 3) Last-login timestamp
        token_login = token.get('last_login')
        user_login  = getattr(user, 'last_login', None)
        print(f"[EnhancedJWT] token_last_login={token_login}, user.last_login={user_login}")
        if token_login and user_login:
            if user_login.isoformat() != token_login:
                print("[EnhancedJWT] Last login mismatch")
                raise AuthenticationFailed(
                    "New login detected; please use a fresh token"
                )

        print("[EnhancedJWT] Token validated successfully")
        return token
