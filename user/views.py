import random
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

@api_view(["GET"])
def get_user_roles(request):
    """API to fetch user role choices"""
    try:
        roles = [
            {"role_name": choice[0], "description": choice[1]}
            for choice in UserRoleModel.ROLE_CHOICES
        ]
        return Response(
            ResponseData.success(data=roles, message="User roles fetched successfully"),
            status=status.HTTP_200_OK,
        )
    except Exception as exception:
        return Response(
            ResponseData.error(str(exception)),
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
    

@api_view(["POST"])
def email_verification(request):
    """API to handle email verification for both tenant and landlord."""
    try:
        # Validate the incoming request data using the serializer (only type validation)
        serializer = EmailVerificationSerializer(data=request.data)
        
        # Check if the serializer data is valid
        if serializer.is_valid():
            # Get the validated data from the serializer
            data = serializer.validated_data
            email = data['email']
            otp = data['otp']
            playerId = data['player_id']

            # Validate OTP and email for tenant first
            try:
                tenant_verification = TenantEmailVerificationModel.objects.get(
                    tenant__email=email,
                    otp=otp,
                    is_verified=False
                )
                # Check OTP expiration
                if now() > tenant_verification.created_at + timedelta(minutes=15):
                    return Response(
                        ResponseData.error("OTP has expired."),
                        status=status.HTTP_400_BAD_REQUEST
                    )
                make_tenant_active = TenantDetailsModel.objects.get(
                                    email=email,
                                )
                if make_tenant_active is not None and not make_tenant_active.is_active:
                    make_tenant_active.is_active = True
                    make_tenant_active.save()
                    DeviceNotificationModel.objects.create(
                        user_id=make_tenant_active.id,
                        player_id=playerId,
                    )
                # If everything is valid, mark it as verified
                tenant_verification.is_verified = True
                tenant_verification.verified_at = now()
                tenant_verification.save()
                return Response(
                    ResponseData.success(make_tenant_active.id,"Email verified successfully for tenant."),
                    status=status.HTTP_200_OK
                )
            except TenantEmailVerificationModel.DoesNotExist:
                pass  # Continue checking for landlord

            # Validate OTP and email for landlord
            try:
                landlord_verification = LandlordEmailVerificationModel.objects.get(
                    landlord__email=email,
                    otp=otp,
                    is_verified=False
                )
                # Check OTP expiration
                if now() > landlord_verification.created_at + timedelta(minutes=15):
                    return Response(
                        ResponseData.error("OTP has expired."),
                        status=status.HTTP_400_BAD_REQUEST
                    )
                make_landlord_active = LandlordDetailsModel.objects.get(
                                    email=email,
                                )
                if make_landlord_active is not None and not make_landlord_active.is_active:
                    make_landlord_active.is_active = True
                    make_landlord_active.save()
                    DeviceNotificationModel.objects.create(
                        user_id=make_landlord_active.id,
                        player_id=playerId,
                    )
                # If everything is valid, mark it as verified
                landlord_verification.is_verified = True
                landlord_verification.verified_at = now()
                landlord_verification.save()

                return Response(
                    ResponseData.success(make_landlord_active.id,"Email verified successfully for landlord."),
                    status=status.HTTP_200_OK
                )
            except LandlordEmailVerificationModel.DoesNotExist:
                pass  # If no match found, raise final validation error

            # If no match found for OTP validation
            return Response(
                ResponseData.error("Invalid email or OTP."),
                status=status.HTTP_400_BAD_REQUEST
            )
        else:
            # If the serializer fails validation (type checking), return errors
            return Response(
                ResponseData.error(serializer.errors),
                status=status.HTTP_400_BAD_REQUEST
            )
    except Exception as e:
        # Handle any other exceptions that occur
        return Response(
            ResponseData.error(str(e)),
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
    
@api_view(["POST"])
def login(request):
    """API to handle user login (for both tenant and landlord)."""
    try:
        # Validate incoming request data using the LoginSerializer
        serializer = LoginSerializer(data=request.data)
        
        # Check if serializer data is valid (type validation only)
        if serializer.is_valid():
            email = serializer.validated_data['email']
            password = serializer.validated_data['password']
            
            # Step 1: Check if the email exists in TenantDetailsModel
            tenant = TenantDetailsModel.objects.filter(email=email, is_active=True).first()
            if tenant:
                # Check if password is correct for tenant
                if check_password(password,tenant.password):
                    return Response(
                        ResponseData.success(data={'user_id': tenant.id, 'user_type': 'tenant'}, message="Login successful for tenant."),
                        status=status.HTTP_200_OK
                    )
                else:
                    return Response(
                        ResponseData.error("Invalid email or password for tenant."),
                        status=status.HTTP_400_BAD_REQUEST
                    )

            # Step 2: Check if the email exists in LandlordDetailsModel
            landlord = LandlordDetailsModel.objects.filter(email=email, is_active=True).first()
            if landlord:
                # Check if password is correct for landlord
                if check_password(password,landlord.password):
                    return Response(
                        ResponseData.success(data={'user_id': landlord.id, 'user_type': 'landlord'}, message="Login successful for landlord."),
                        status=status.HTTP_200_OK
                    )
                else:
                    return Response(
                        ResponseData.error("Invalid email or password for landlord."),
                        status=status.HTTP_400_BAD_REQUEST
                    )

            # If no matching tenant or landlord found
            return Response(
                ResponseData.error("Invalid email or password."),
                status=status.HTTP_400_BAD_REQUEST
            )

        # If the serializer fails type validation
        return Response(
            ResponseData.error(serializer.errors),
            status=status.HTTP_400_BAD_REQUEST
        )

    except Exception as e:
        # Handle any other unexpected errors
        return Response(
            ResponseData.error(str(e)),
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
    
@api_view(["POST"])
def forgot_password(request):
    """API to handle forgot password request."""
    try:
        # Validate the incoming request data using the serializer
        serializer = ForgotPasswordSerializer(data=request.data)
        
        # Check if the serializer data is valid
        if serializer.is_valid():
            email = serializer.validated_data['email']

            # Check if the email exists in the TenantDetailsModel
            tenant = TenantDetailsModel.objects.filter(email=email,is_active=True).first()
            if tenant:
                # Generate new OTP for tenant
                otp = str(random.randint(100000, 999999))  # Generate a new OTP
                tenant_verification = TenantEmailVerificationModel.objects.filter(
                    tenant=tenant,
                    is_verified=False
                ).first()

                if tenant_verification:
                    tenant_verification.otp = otp
                    tenant_verification.created_at = now()
                    tenant_verification.save()
                    send_otp_email(tenant.email, otp)  # Send OTP to tenant's email

                else:
                    # No unverified OTP, create new verification entry
                    TenantEmailVerificationModel.objects.create(
                        tenant=tenant,
                        otp=otp,
                        is_verified=False,
                        created_at=now()
                    )
                send_otp_email(tenant.email, otp)

                return Response(
                    ResponseData.success_without_data("OTP sent to tenant for password reset."),
                    status=status.HTTP_200_OK
                )

            # Check if the email exists in the LandlordDetailsModel
            landlord = LandlordDetailsModel.objects.filter(email=email).first()
            if landlord:
                # Generate new OTP for landlord
                otp = str(random.randint(100000, 999999))  # Generate a new OTP
                landlord_verification = LandlordEmailVerificationModel.objects.filter(
                    landlord=landlord,
                    is_verified=False
                ).first()

                if landlord_verification:
                    landlord_verification.otp = otp
                    landlord_verification.created_at = now()
                    landlord_verification.save()
                    send_otp_email(landlord.email, otp)  # Send OTP to landlord's email

                else:
                    # No unverified OTP, create new verification entry
                    LandlordEmailVerificationModel.objects.create(
                        landlord=landlord,
                        otp=otp,
                        is_verified=False,
                        created_at=now()
                    )
                    send_otp_email(landlord.email, otp)

                return Response(
                    ResponseData.success_without_data("OTP sent to landlord for password reset."),
                    status=status.HTTP_200_OK
                )

            # If the email doesn't exist in both TenantDetailsModel and LandlordDetailsModel
            return Response(
                ResponseData.error("Email not found for tenant or landlord."),
                status=status.HTTP_400_BAD_REQUEST
            )
        else:
            # If the serializer fails validation (type checking), return errors
            return Response(
                ResponseData.error(serializer.errors),
                status=status.HTTP_400_BAD_REQUEST
            )
    except Exception as e:
        # Handle any other exceptions that occur
        return Response(
            ResponseData.error(str(e)),
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
    
@api_view(["POST"])
def update_password(request):
    """API to handle password update."""
    try:
        print(request.data)
        # Validate the incoming request data using the serializer
        serializer = PasswordUpdateSerializer(data=request.data)

        if serializer.is_valid():
            email = serializer.validated_data['email']
            new_password = serializer.validated_data['new_password']

            # First, check if the email exists for the tenant or landlord
            tenant = TenantDetailsModel.objects.filter(email=email, is_active=True).first()
            if tenant:

                # Update the password for the tenant
                tenant.password = make_password(new_password)
                tenant.save()

                return Response(
                    ResponseData.success_without_data("Password updated successfully for tenant."),
                    status=status.HTTP_200_OK
                )

            landlord = LandlordDetailsModel.objects.filter(email=email,is_active=True).first()
            if landlord:
                # Update the password for the landlord
                landlord.password = make_password(new_password)
                landlord.save()
                return Response(
                    ResponseData.success_without_data("Password updated successfully for landlord."),
                    status=status.HTTP_200_OK
                )

            # If the email does not exist for either tenant or landlord
            return Response(
                ResponseData.error("Email not found for tenant or landlord."),
                status=status.HTTP_400_BAD_REQUEST
            )

        # If the serializer fails validation
        return Response(
            {"error": serializer.errors},
            status=status.HTTP_400_BAD_REQUEST
        )
    except Exception as e:
        return Response(
            {"error": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )