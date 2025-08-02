import random
from rest_framework_simplejwt.tokens import RefreshToken, TokenError
import boto3
from django.utils.timezone import now, timedelta
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from landlord.models import LandlordDetailsModel, LandlordEmailVerificationModel
from tenant.models import TenantDetailsModel, TenantEmailVerificationModel
from tenant.views import send_otp_email
from rest_framework_simplejwt.exceptions import InvalidToken,ExpiredTokenError
from rest_framework_simplejwt.tokens import UntypedToken

from user.jwt_utils import get_tokens_for_user, refresh_access_token
from user.static_strings import OTP_SMS_MESSAGE
from .models import UserRoleModel
from response import Response as ResponseData
from user.authentication import EnhancedJWTValidation
from rest_framework.permissions import IsAuthenticated
from .serializers import EmailVerificationSerializer, ForgotPasswordSerializer, LoginSerializer, PasswordUpdateSerializer
from django.contrib.auth.hashers import check_password  # For verifying password hash
from django.contrib.auth.hashers import make_password
from .serializers import OTPSendSerializer, OTPVerifySerializer
from .models import OTPModel  # Ensure your OTPModel is imported correctly
from response import Response as ResponseData
from user.authentication import EnhancedJWTValidation
from rest_framework.permissions import IsAuthenticated  # Assuming you have a ResponseData helper
from dotenv import load_dotenv
import os
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth import authenticate
from rest_framework.decorators import api_view, permission_classes, authentication_classes
from rest_framework.permissions import AllowAny
from rest_framework.authentication import SessionAuthentication
from rest_framework_simplejwt.authentication import JWTAuthentication

# Load environment variables
load_dotenv()

# Import our translation helper
from translation_utils import get_translation, DEFAULT_LANGUAGE_CODE
    
@api_view(["POST"])
@authentication_classes([EnhancedJWTValidation, SessionAuthentication])
@permission_classes([AllowAny])
def email_verification(request):
    """API to handle email verification for both tenant and landlord."""
    language_code = request.data.get("language_code", DEFAULT_LANGUAGE_CODE)
    try:
        serializer = EmailVerificationSerializer(data=request.data)
        if serializer.is_valid():
            data = serializer.validated_data
            email = data['email']
            otp = data['otp']

            # Validate OTP and email for tenant first
            try:
                tenant_verification = TenantEmailVerificationModel.objects.get(
                    tenant__email=email,
                    otp=otp,
                    is_verified=False
                )
                if now() > tenant_verification.created_at + timedelta(minutes=15):
                    message = get_translation("ERR_OTP_EXPIRED", language_code)
                    return Response(
                        ResponseData.error(message),
                        status=status.HTTP_400_BAD_REQUEST
                    )
                make_tenant_active = TenantDetailsModel.objects.get(email=email)
                if make_tenant_active is not None and not make_tenant_active.is_active:
                    make_tenant_active.is_active = True
                    make_tenant_active.save()
                tenant_verification.is_verified = True
                tenant_verification.verified_at = now()
                tenant_verification.save()
                message = get_translation("SUCC_EMAIL_VERIFIED_TENANT", language_code)
                tokens = get_tokens_for_user(make_tenant_active)
                return Response(
                    ResponseData.success(
                        {
                            'tokens' : tokens,
                            'id' : make_tenant_active.id
                        }, message),
                    status=status.HTTP_200_OK
                )
            except TenantEmailVerificationModel.DoesNotExist:
                pass  # Continue checking for landlord

            try:
                landlord_verification = LandlordEmailVerificationModel.objects.get(
                    landlord__email=email,
                    otp=otp,
                    is_verified=False
                )
                if now() > landlord_verification.created_at + timedelta(minutes=15):
                    message = get_translation("ERR_OTP_EXPIRED", language_code)
                    return Response(
                        ResponseData.error(message),
                        status=status.HTTP_400_BAD_REQUEST
                    )
                make_landlord_active = LandlordDetailsModel.objects.get(email=email)
                if make_landlord_active is not None and not make_landlord_active.is_active:
                    make_landlord_active.is_active = True
                    make_landlord_active.save()
                landlord_verification.is_verified = True
                landlord_verification.verified_at = now()
                landlord_verification.save()
                message = get_translation("SUCC_EMAIL_VERIFIED_LANDLORD", language_code)
                tokens = get_tokens_for_user(make_landlord_active)
                return Response(
                    ResponseData.success(
                        data={
                            'tokens' : tokens,
                            'id' : make_landlord_active.id
                        }, message=message),
                    status=status.HTTP_200_OK
                )
            except LandlordEmailVerificationModel.DoesNotExist:
                pass

            message = get_translation("ERR_INVALID_EMAIL_OR_OTP", language_code)
            return Response(
                ResponseData.error(message),
                status=status.HTTP_400_BAD_REQUEST
            )
        else:
            return Response(
                ResponseData.error(serializer.errors),
                status=status.HTTP_400_BAD_REQUEST
            )
    except Exception as e:
        return Response(
            ResponseData.error(str(e)),
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(["POST"])
@authentication_classes([EnhancedJWTValidation, SessionAuthentication])
@permission_classes([AllowAny])
def login(request):
    """Secure login API with enhanced JWT tokens"""
    language_code = request.data.get("language_code", DEFAULT_LANGUAGE_CODE)
    try:
        serializer = LoginSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                ResponseData.error(serializer.errors),
                status=status.HTTP_400_BAD_REQUEST
            )

        email = serializer.validated_data['email']
        password = serializer.validated_data['password']
        isLandlord = serializer.validated_data['isLandlord']
        print(f'passwordpassword {email} {password}')
        if not isLandlord:
            # Tenant login flow
            tenant = TenantDetailsModel.objects.filter(email=email, is_active=True).first()
            if tenant:
                if password != '' and not tenant.is_google_account:
                    if check_password(password, tenant.password):
                        tokens = get_tokens_for_user(tenant)
                        message = get_translation("SUCC_LOGIN_TENANT", language_code)
                        return Response(
                            ResponseData.success(
                                data={
                                    'user_id': tenant.id,
                                    'user_type': 'tenant',
                                    'email': tenant.email,  # Include email in response
                                    'tokens': tokens
                                },
                                message=message
                            ),
                            status=status.HTTP_200_OK
                        )
                    else:
                        message = get_translation("ERR_INVALID_EMAIL_OR_PASSWORD_TENANT", language_code)
                        return Response(
                            ResponseData.error(message),
                            status=status.HTTP_400_BAD_REQUEST
                        )
                elif tenant.is_google_account and password == '':
                    tokens = get_tokens_for_user(tenant)
                    message = get_translation("SUCC_LOGIN_TENANT", language_code)
                    return Response(
                        ResponseData.success(
                            data={
                                'email': tenant.email,
                                'user_id': tenant.id,
                                'user_type': 'tenant',
                                'tokens': tokens
                            },
                            message=message
                        ),
                        status=status.HTTP_200_OK
                    )

        else:
            # Landlord login flow
            landlord = LandlordDetailsModel.objects.filter(email=email, is_active=True).first()
            if landlord:
                print('111')
                if password != '' and not landlord.is_google_account:
                    print('222')
                    if check_password(password, landlord.password):
                        tokens = get_tokens_for_user(landlord)
                        message = get_translation("SUCC_LOGIN_LANDLORD", language_code)
                        return Response(
                            ResponseData.success(
                                data={
                                    'user_id': landlord.id,
                                    'user_type': 'landlord',
                                    'email': landlord.email,
                                    'tokens': tokens
                                },
                                message=message
                            ),
                            status=status.HTTP_200_OK
                        )
                    else:
                        message = get_translation("ERR_INVALID_EMAIL_OR_PASSWORD_LANDLORD", language_code)
                        return Response(
                            ResponseData.error(message),
                            status=status.HTTP_400_BAD_REQUEST
                        )
                elif landlord.is_google_account and password == '':
                    tokens = get_tokens_for_user(landlord)
                    message = get_translation("SUCC_LOGIN_LANDLORD", language_code)
                    return Response(
                        ResponseData.success(
                            data={
                                'user_id': landlord.id,
                                'email': landlord.email,
                                'user_type': 'landlord',
                                'tokens': tokens
                            },
                            message=message
                        ),
                        status=status.HTTP_200_OK
                    )

        # No valid user found
        message = get_translation("ERR_INVALID_EMAIL_OR_PASSWORD", language_code)
        return Response(
            ResponseData.error(message),
            status=status.HTTP_400_BAD_REQUEST
        )

    except Exception as e:
        return Response(
            ResponseData.error(str(e)),
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(["POST"])
@permission_classes([AllowAny])
def refresh_token(request):
    """Secure token refresh with validation"""
    print("\n[Token Refresh] === Starting token refresh process ===")
    try:
        refresh_token_str = request.data.get('refresh')
        print(f"[Token Refresh] Incoming request data: {request.data}")

        if not refresh_token_str:
            print("[Token Refresh] ❌ Error: No refresh token provided")
            return Response(
                ResponseData.error("Refresh token is required"),
                status=status.HTTP_400_BAD_REQUEST
            )

        # Validate refresh token and get payload
        try:
            print("[Token Refresh] Validating refresh token...")
            refresh = RefreshToken(refresh_token_str)
            payload = refresh.payload
        except TokenError as e:
            print(f"[Token Refresh] ❌ Token error: {e}")
            return Response(
                ResponseData.error("Invalid or expired refresh token"),
                status=status.HTTP_401_UNAUTHORIZED
            )

        # Extract claims
        user_id = payload.get('user_id')
        user_type = (payload.get('user_type') or "").lower()
        email = payload.get('email')
        token_pw = payload.get('pw_hash')

        print(f"[Token Refresh] Extracted claims - user_id: {user_id}, user_type: {user_type}, email: {email}, pw_hash: {token_pw!r}")

        # Lookup user
        if user_type == 'tenant':
            print("[Token Refresh] Looking up tenant user...")
            user = TenantDetailsModel.objects.filter(id=user_id, email=email, is_active=True).first()
        else:
            print("[Token Refresh] Looking up landlord user...")
            user = LandlordDetailsModel.objects.filter(id=user_id, email=email, is_active=True).first()

        if not user:
            print("[Token Refresh] ❌ Error: User not found or inactive")
            return Response(
                ResponseData.error("User not found"),
                status=status.HTTP_401_UNAUTHORIZED
            )

        print(f"[Token Refresh] Found active user: {user}")

        # Compare password hash
        if hasattr(user, 'has_usable_password') and user.has_usable_password():
            current_pw_fragment = user.password[:15]
        else:
            current_pw_fragment = ''

        print(f"[Token Refresh] Password check - Current: {current_pw_fragment!r}, Token: {token_pw!r}")
        if token_pw != current_pw_fragment:
            print("[Token Refresh] ❌ Error: Password changed")
            return Response(
                ResponseData.error("Password changed - please login again"),
                status=status.HTTP_401_UNAUTHORIZED
            )

        print("[Token Refresh] ✅ Password version validated")

        # Rotate tokens
        print("[Token Refresh] Generating new tokens...")
        result = refresh_access_token(refresh_token_str)
        if 'error' in result:
            print(f"[Token Refresh] ❌ Refresh error: {result['error']}")
            return Response(
                ResponseData.error(result['error']),
                status=status.HTTP_401_UNAUTHORIZED
            )

        print(f"[Token Refresh] ✅ Successfully generated new tokens. Result: {result}")
        return Response(
            ResponseData.success(data=result, message='Refresh token generated'),
            status=status.HTTP_200_OK
        )

    except Exception as e:
        print(f"[Token Refresh] ❌ Unexpected error: {e}")
        import traceback; traceback.print_exc()
        return Response(
            ResponseData.error("Internal server error"),
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
    finally:
        print("[Token Refresh] === Refresh process completed ===\n")
        
@api_view(["POST"])
#@authentication_classes([EnhancedJWTValidation, SessionAuthentication])
@permission_classes([AllowAny])
def forgot_password(request):
    """API to handle forgot password request."""
    language_code = request.data.get("language_code", DEFAULT_LANGUAGE_CODE)
    try:
        serializer = ForgotPasswordSerializer(data=request.data)
        if serializer.is_valid():
            email = serializer.validated_data['email']

            tenant = TenantDetailsModel.objects.filter(email=email, is_active=True).first()
            if tenant:
                otp = str(random.randint(100000, 999999))
                tenant_verification = TenantEmailVerificationModel.objects.filter(
                    tenant=tenant,
                    is_verified=False
                ).first()

                if tenant_verification:
                    tenant_verification.otp = otp
                    tenant_verification.created_at = now()
                    tenant_verification.save()
                    send_otp_email(tenant.email, otp)
                else:
                    TenantEmailVerificationModel.objects.create(
                        tenant=tenant,
                        otp=otp,
                        is_verified=False,
                        created_at=now()
                    )
                    send_otp_email(tenant.email, otp)

                message = get_translation("SUCC_OTP_SENT_TENANT", language_code)
                return Response(
                    ResponseData.success_without_data(message),
                    status=status.HTTP_200_OK
                )

            landlord = LandlordDetailsModel.objects.filter(email=email).first()
            if landlord:
                otp = str(random.randint(100000, 999999))
                landlord_verification = LandlordEmailVerificationModel.objects.filter(
                    landlord=landlord,
                    is_verified=False
                ).first()

                if landlord_verification:
                    landlord_verification.otp = otp
                    landlord_verification.created_at = now()
                    landlord_verification.save()
                    send_otp_email(landlord.email, otp)
                else:
                    LandlordEmailVerificationModel.objects.create(
                        landlord=landlord,
                        otp=otp,
                        is_verified=False,
                        created_at=now()
                    )
                    send_otp_email(landlord.email, otp)

                message = get_translation("SUCC_OTP_SENT_LANDLORD", language_code)
                return Response(
                    ResponseData.success_without_data(message),
                    status=status.HTTP_200_OK
                )

            message = get_translation("ERR_EMAIL_NOT_FOUND", language_code)
            return Response(
                ResponseData.error(message),
                status=status.HTTP_400_BAD_REQUEST
            )
        else:
            return Response(
                ResponseData.error(serializer.errors),
                status=status.HTTP_400_BAD_REQUEST
            )
    except Exception as e:
        return Response(
            ResponseData.error(str(e)),
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
    
@api_view(["POST"])
@authentication_classes([EnhancedJWTValidation, SessionAuthentication])
@permission_classes([AllowAny])
def update_password(request):
    """API to handle password update."""
    language_code = request.data.get("language_code", DEFAULT_LANGUAGE_CODE)
    try:
        print(request.data)
        serializer = PasswordUpdateSerializer(data=request.data)
        if serializer.is_valid():
            email = serializer.validated_data['email']
            new_password = serializer.validated_data['new_password']

            tenant = TenantDetailsModel.objects.filter(email=email, is_active=True).first()
            if tenant:
                tenant.password = make_password(new_password)
                tenant.save()
                message = get_translation("SUCC_PASSWORD_UPDATED_TENANT", language_code)
                return Response(
                    ResponseData.success_without_data(message),
                    status=status.HTTP_200_OK
                )

            landlord = LandlordDetailsModel.objects.filter(email=email, is_active=True).first()
            if landlord:
                print(f'new_password {new_password}')
                landlord.password = make_password(new_password)
                print(f'new_password_after {new_password}')
                landlord.save()
                message = get_translation("SUCC_PASSWORD_UPDATED_LANDLORD", language_code)
                return Response(
                    ResponseData.success_without_data(message),
                    status=status.HTTP_200_OK
                )

            message = get_translation("ERR_EMAIL_NOT_FOUND", language_code)
            return Response(
                ResponseData.error(message),
                status=status.HTTP_400_BAD_REQUEST
            )

        return Response(
            {"error": serializer.errors},
            status=status.HTTP_400_BAD_REQUEST
        )
    except Exception as e:
        return Response(
            {"error": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
    
# Initialize SNS client for AWS SNS SMS
sns_client = boto3.client(
    'sns',
    aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
    aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
    region_name='eu-central-1'
)

def send_sms(phone_number, message):
    response = sns_client.publish(
        PhoneNumber=phone_number,
        Message=message,
        MessageAttributes={
            'AWS.SNS.SMS.SenderID': {
                'DataType': 'String',
                'StringValue': 'OTPAPP'
            },
            'AWS.SNS.SMS.SMSType': {
                'DataType': 'String',
                'StringValue': 'Transactional'
            }
        }
    )
    return response

@api_view(["POST"])
@authentication_classes([EnhancedJWTValidation, SessionAuthentication])
@permission_classes([IsAuthenticated])
def send_otp(request):
    """
    API to send an OTP SMS.
    Expected JSON payload:
    {
        "phone_number": "+491628893421",
        "user_id": "123",          # can be a string or number
        "role_name": "tenant"      # or "landlord"
    }
    """
    language_code = request.data.get("language_code", DEFAULT_LANGUAGE_CODE)
    serializer = OTPSendSerializer(data=request.data)
    if serializer.is_valid():
        phone_number = serializer.validated_data['phone_number']
        user_id = serializer.validated_data['user_id']
        role_name = serializer.validated_data['role_name']
        # ── early‐out if this phone is already in use in either model ──
        already_in_tenants  = TenantDetailsModel.objects.filter(phone_number=phone_number,is_active=True).exists()
        already_in_landlords = LandlordDetailsModel.objects.filter(phone_number=phone_number,is_active=True).exists()

        if already_in_tenants or already_in_landlords:
            return Response(
                ResponseData.error("This phone number is already registered."),
                status=status.HTTP_409_CONFLICT
            )
        otp = str(random.randint(100000, 999999))
        
        OTPModel.objects.update_or_create(
            role_name=role_name,
            phone_number=phone_number,
            defaults={
                'otp': otp,
                'is_verified': False,
                'created_at': now(),
                'verified_at': None
            }
        )
        
        try:
            send_sms(phone_number, OTP_SMS_MESSAGE.format(otp))
        except Exception as e:
            return Response(
                ResponseData.error(str(e)),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
        message = get_translation("SUCC_OTP_SENT_SMS", language_code)
        return Response(
            ResponseData.success_without_data(message),
            status=status.HTTP_200_OK
        )
    else:
        return Response(
            ResponseData.error(serializer.errors),
            status=status.HTTP_400_BAD_REQUEST
        )

@api_view(["POST"])
@authentication_classes([EnhancedJWTValidation, SessionAuthentication])
@permission_classes([IsAuthenticated])
def verify_otp(request):
    """
    API to verify an OTP.
    Expected JSON payload:
    {
        "phone_number": "+491628893421",
        "user_id": "123",
        "role_name": "tenant",      # or "landlord"
        "otp": "123456"
    }
    """
    language_code = request.data.get("language_code", DEFAULT_LANGUAGE_CODE)
    serializer = OTPVerifySerializer(data=request.data)
    if serializer.is_valid():
        phone_number = serializer.validated_data['phone_number']
        user_id = serializer.validated_data['user_id']
        role_name = serializer.validated_data['role_name']
        otp_received = serializer.validated_data['otp']
        
        try:
            otp_obj = OTPModel.objects.get(role_name=role_name, phone_number=phone_number, is_verified=False)
        except OTPModel.DoesNotExist:
            message = get_translation("ERR_INVALID_PHONE_OR_OTP", language_code)
            return Response(
                ResponseData.error(message),
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if now() > otp_obj.created_at + timedelta(minutes=15):
            message = get_translation("ERR_OTP_EXPIRED", language_code)
            return Response(
                ResponseData.error(message),
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if otp_obj.otp != otp_received:
            message = get_translation("ERR_INVALID_OTP", language_code)
            return Response(
                ResponseData.error(message),
                status=status.HTTP_400_BAD_REQUEST
            )
        
        otp_obj.is_verified = True
        otp_obj.verified_at = now()
        otp_obj.save()
        
        if role_name == "tenant":
            tenant = TenantDetailsModel.objects.filter(id=user_id).first()
            if tenant:
                tenant.phone_number = phone_number
                tenant.save()
            else:
                message = get_translation("ERR_TENANT_NOT_FOUND", language_code)
                return Response(
                    ResponseData.error(message),
                    status=status.HTTP_400_BAD_REQUEST
                )
        elif role_name == "landlord":
            landlord = LandlordDetailsModel.objects.filter(id=user_id).first()
            if landlord:
                landlord.phone_number = phone_number
                landlord.save()
            else:
                message = get_translation("ERR_LANDLORD_NOT_FOUND", language_code)
                return Response(
                    ResponseData.error(message),
                    status=status.HTTP_400_BAD_REQUEST
                )
        else:
            message = get_translation("ERR_INVALID_ROLE_NAME", language_code)
            return Response(
                ResponseData.error(message),
                status=status.HTTP_400_BAD_REQUEST
            )
        
        message = get_translation("SUCC_PHONE_VERIFIED", language_code)
        return Response(
            ResponseData.success_without_data(message),
            status=status.HTTP_200_OK
        )
    else:
        return Response(
            ResponseData.error(serializer.errors),
            status=status.HTTP_400_BAD_REQUEST
        )
