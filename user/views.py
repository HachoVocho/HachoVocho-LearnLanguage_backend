import random
import boto3
from django.utils.timezone import now, timedelta
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status

from landlord.models import LandlordDetailsModel, LandlordEmailVerificationModel
from notifications.models import DeviceNotificationModel
from tenant.models import TenantDetailsModel, TenantEmailVerificationModel
from tenant.views import send_otp_email
from .models import UserRoleModel
from response import Response as ResponseData
from .serializers import EmailVerificationSerializer, ForgotPasswordSerializer, LoginSerializer, PasswordUpdateSerializer
from django.contrib.auth.hashers import check_password  # For verifying password hash
from django.contrib.auth.hashers import make_password
from .serializers import OTPSendSerializer, OTPVerifySerializer
from .models import OTPModel  # Ensure your OTPModel is imported correctly
from response import Response as ResponseData  # Assuming you have a ResponseData helper
from dotenv import load_dotenv
import os
# Load environment variables
load_dotenv()

# Import our translation helper
from translation_utils import get_translation, DEFAULT_LANGUAGE_CODE
    

@api_view(["POST"])
def email_verification(request):
    """API to handle email verification for both tenant and landlord."""
    language_code = request.data.get("language_code", DEFAULT_LANGUAGE_CODE)
    try:
        serializer = EmailVerificationSerializer(data=request.data)
        if serializer.is_valid():
            data = serializer.validated_data
            email = data['email']
            otp = data['otp']
            playerId = data['player_id'] if 'player_id' in request.data else ''

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
                    notification, created = DeviceNotificationModel.objects.get_or_create(
                        player_id=playerId,
                        defaults={'user_id': make_tenant_active.id},
                    )
                tenant_verification.is_verified = True
                tenant_verification.verified_at = now()
                tenant_verification.save()
                message = get_translation("SUCC_EMAIL_VERIFIED_TENANT", language_code)
                return Response(
                    ResponseData.success(make_tenant_active.id, message),
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
                    DeviceNotificationModel.objects.create(
                        user_id=make_landlord_active.id,
                        player_id=playerId,
                    )
                landlord_verification.is_verified = True
                landlord_verification.verified_at = now()
                landlord_verification.save()
                message = get_translation("SUCC_EMAIL_VERIFIED_LANDLORD", language_code)
                return Response(
                    ResponseData.success(make_landlord_active.id, message),
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
def login(request):
    """API to handle user login (for both tenant and landlord)."""
    print(f'request.data {request.data}')
    language_code = request.data.get("language_code", DEFAULT_LANGUAGE_CODE)
    try:
        serializer = LoginSerializer(data=request.data)
        if serializer.is_valid():
            email = serializer.validated_data['email']
            password = serializer.validated_data['password']
            
            tenant = TenantDetailsModel.objects.filter(email=email, is_active=True).first()
            if tenant and tenant.password != '' and password != '':
                if check_password(password, tenant.password):
                    message = get_translation("SUCC_LOGIN_TENANT", language_code)
                    return Response(
                        ResponseData.success(data={'user_id': tenant.id, 'user_type': 'tenant'}, message=message),
                        status=status.HTTP_200_OK
                    )
                else:
                    message = get_translation("ERR_INVALID_EMAIL_OR_PASSWORD_TENANT", language_code)
                    return Response(
                        ResponseData.error(message),
                        status=status.HTTP_400_BAD_REQUEST
                    )
            if tenant and password == '':
                message = get_translation("SUCC_LOGIN_TENANT", language_code)
                return Response(
                    ResponseData.success(data={'user_id': tenant.id, 'user_type': 'tenant'}, message=message),
                    status=status.HTTP_200_OK
                )

            landlord = LandlordDetailsModel.objects.filter(email=email, is_active=True).first()
            if landlord and landlord.password != '':
                if check_password(password, landlord.password):
                    message = get_translation("SUCC_LOGIN_LANDLORD", language_code)
                    return Response(
                        ResponseData.success(data={'user_id': landlord.id, 'user_type': 'landlord'}, message=message),
                        status=status.HTTP_200_OK
                    )
                else:
                    message = get_translation("ERR_INVALID_EMAIL_OR_PASSWORD_LANDLORD", language_code)
                    return Response(
                        ResponseData.error(message),
                        status=status.HTTP_400_BAD_REQUEST
                    )
            if landlord and landlord.password == '':
                message = get_translation("SUCC_LOGIN_LANDLORD", language_code)
                return Response(
                    ResponseData.success(data={'user_id': landlord.id, 'user_type': 'landlord'}, message=message),
                    status=status.HTTP_200_OK
                )
            message = get_translation("ERR_INVALID_EMAIL_OR_PASSWORD", language_code)
            return Response(
                ResponseData.error(message),
                status=status.HTTP_400_BAD_REQUEST
            )

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
                landlord.password = make_password(new_password)
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

        otp = str(random.randint(100000, 999999))
        
        otp_obj, created = OTPModel.objects.update_or_create(
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
