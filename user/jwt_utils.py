import datetime
from django.conf import settings
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.serializers import TokenRefreshSerializer
from django.contrib.auth.hashers import make_password

# Import your profile models so you can detect them
from tenant.models import TenantDetailsModel
from landlord.models import LandlordDetailsModel
from user.serializers import NoUserLookupTokenRefreshSerializer

def get_tokens_for_user(user):
    """
    Creates JWT with these enhanced claims:
      - user_id
      - user_type ('tenant' or 'landlord')
      - email
      - pw_hash fragment (empty if no usable password)
      - last_login timestamp
    """
    refresh = RefreshToken.for_user(user)
    
    # Core identity claims
    refresh['user_id'] = user.id

    # Ensure user_type is a real string
    if isinstance(user, TenantDetailsModel):
        refresh['user_type'] = 'tenant'
    elif isinstance(user, LandlordDetailsModel):
        refresh['user_type'] = 'landlord'
    else:
        refresh['user_type'] = 'unknown'

    refresh['email'] = user.email

    # Password‐hash fragment (empty for social/no‐password users)
    if hasattr(user, 'has_usable_password') and user.has_usable_password():
        pw_fragment = make_password(user.password)[:15]
    else:
        pw_fragment = ''
    refresh['pw_hash'] = pw_fragment

    # Last login (ISO) if available
    refresh['last_login'] = user.last_login.isoformat() if getattr(user, 'last_login', None) else None
    
    return {
        'refresh': str(refresh),
        'access':  str(refresh.access_token),
    }

def refresh_access_token(refresh_token):
    """
    Refresh an access token using a refresh token,
    but skip the built-in user lookup.
    """
    serializer = NoUserLookupTokenRefreshSerializer(data={"refresh": refresh_token})
    try:
        serializer.is_valid(raise_exception=True)
        return {
            "access":  serializer.validated_data["access"],
            "refresh": serializer.validated_data["refresh"],
        }
    except Exception as e:
        # e could be a TokenError wrapped by the serializer
        return {"error": str(e)}

