# your_app/ws_auth.py

import json
from django.contrib.auth.models import AnonymousUser
from rest_framework_simplejwt.tokens import AccessToken, TokenError
from tenant.models import TenantDetailsModel
from landlord.models import LandlordDetailsModel

async def authenticate_websocket(scope):
    """
    Pulls the JWT from scope['subprotocol'], validates it, and returns (user, error_code).
    Prints debug info at each step.
    """
    # 1) Read the single negotiated subprotocol
    print(f'scopedssdv {scope}')
    proto = scope.get("subprotocols")[0]
    print(f"[WS Auth] negotiated subprotocol: {proto!r}")
    token = None

    if isinstance(proto, str) and proto.lower().startswith("bearer "):
        token = proto.split(" ", 1)[1]
        print(f"[WS Auth] extracted token from subprotocol")

    if not token:
        print("[WS Auth] no token found in subprotocol → missing_token")
        return AnonymousUser(), "missing_token"

    try:
        # 2) Validate token signature & expiry
        access_token = AccessToken(token)
        print(f'access_token {access_token}')
        print(f"[WS Auth] token valid, payload iat={access_token['iat']}, exp={access_token['exp']}")

        # 3) Read claims
        user_id   = access_token["user_id"]
        user_type = (access_token.get("user_type") or "").lower()
        print(f"[WS Auth] user_id={user_id}, user_type={user_type}")

        # 4) Lookup the correct model
        if user_type == "tenant":
            user = await TenantDetailsModel.objects.aget(id=user_id)
            print("[WS Auth] TenantDetailsModel loaded")
        elif user_type == "landlord":
            user = await LandlordDetailsModel.objects.aget(id=user_id)
            print("[WS Auth] LandlordDetailsModel loaded")
        else:
            print("[WS Auth] unknown user_type in token")
            return AnonymousUser(), "unknown_user_type"

        return user, None

    except TokenError as e:
        print(f"[WS Auth] TokenError during validation: {e}")
        return AnonymousUser(), f"token_error:{e}"

    except TenantDetailsModel.DoesNotExist:
        print(f"[WS Auth] No TenantDetailsModel found for id={user_id}")
        return AnonymousUser(), "tenant_not_found"

    except LandlordDetailsModel.DoesNotExist:
        print(f"[WS Auth] No LandlordDetailsModel found for id={user_id}")
        return AnonymousUser(), "landlord_not_found"

    except Exception as e:
        print(f"[WS Auth] Unexpected error: {e!r}")
        return AnonymousUser(), f"unexpected_error:{e}"
