# payments/views.py
from datetime import timedelta
from django.http import Http404
from django.shortcuts import get_object_or_404
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from django.utils import timezone
from landlord.models import LandlordRoomWiseBedModel
from localization.models import CountryModel
from payments.models import TenantPaymentModel
from tenant.models import TenantDetailsModel, TenantPersonalityDetailsModel
from .serializers import TenantPaymentSerializer, TenantSubscriptionStatusSerializer
from response import Response as ResponseData
from django.db import transaction
from rest_framework.permissions import IsAuthenticated  # Adjust import according to your project structure
from django.conf import settings
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
import braintree
from rest_framework.permissions import AllowAny
from rest_framework.authentication import SessionAuthentication
from user.authentication import EnhancedJWTValidation
from rest_framework.decorators import api_view, permission_classes, authentication_classes
from rest_framework_simplejwt.authentication import JWTAuthentication
gateway = braintree.BraintreeGateway(
    braintree.Configuration(
        environment=getattr(braintree.Environment, settings.BRAINTREE_ENVIRONMENT),
        merchant_id=settings.BRAINTREE_MERCHANT_ID,
        public_key=settings.BRAINTREE_PUBLIC_KEY,
        private_key=settings.BRAINTREE_PRIVATE_KEY,
    )
)

@api_view(["GET"])
@authentication_classes([EnhancedJWTValidation, SessionAuthentication])
@permission_classes([IsAuthenticated])
def generate_client_token(request):
    """
    Generate a Braintree client token for use on the client side.
    """
    try:
        client_token = gateway.client_token.generate()
        return Response(
            ResponseData.success(client_token, "Client token generated"),
            status=status.HTTP_200_OK
        )
    except Exception as e:
        return Response(
            ResponseData.error("Error generating client token", str(e)),
            status=status.HTTP_400_BAD_REQUEST
        )


@api_view(["POST"])
@authentication_classes([EnhancedJWTValidation, SessionAuthentication])
@permission_classes([IsAuthenticated])
def process_payment(request):
    """
    Process a payment using a payment method nonce obtained from the Flutter app.
    Expected data: { "nonce": "nonce-from-client", "amount": "10.00", "tenant_id": <tenant id> }
    """
    print(f'request.data {request.data}')
    nonce_from_client = request.data.get("nonce")
    amount = request.data.get("amount")
    currency_symbol = request.data.get("currency_symbol")
    tenant_id = request.data.get("tenant_id")

    if not nonce_from_client or not amount or not tenant_id:
        return Response(
            ResponseData.error("Missing nonce, amount or tenant_id"),
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        result = gateway.transaction.sale({
            "amount": amount,
            "payment_method_nonce": nonce_from_client,
            "options": {
                "submit_for_settlement": True
            }
        })

        if result.is_success:
            transaction = result.transaction
            try:
                tenant = TenantDetailsModel.objects.get(id=tenant_id, is_active=True)
            except TenantDetailsModel.DoesNotExist:
                return Response(
                    ResponseData.error("Tenant not found"),
                    status=status.HTTP_404_NOT_FOUND
                )

            # Save the payment details in TenantPaymentModel
            TenantPaymentModel.objects.create(
                tenant=tenant,
                amount=transaction.amount,
                country=tenant.preferred_city.state.country,
                transaction_id=transaction.id,
                status=transaction.status
            )

            return Response(
                ResponseData.success_without_data("Transaction successful"),
                status=status.HTTP_200_OK
            )
        else:
            return Response(
                ResponseData.error(result.message),
                status=status.HTTP_400_BAD_REQUEST
            )
    except Exception as e:
        return Response(
            ResponseData.error(str(e)),
            status=status.HTTP_400_BAD_REQUEST
        )

    
@api_view(['POST'])
@authentication_classes([EnhancedJWTValidation, SessionAuthentication])
@permission_classes([IsAuthenticated])
def tenant_payment_history(request):
    """
    POST /api/payments/history/
    Body: { "tenant_id": <integer> }

    Returns all non-deleted payments for the given tenant, newest first,
    and formats the amount with its currency symbol.
    """
    tenant_id = request.data.get('tenant_id')
    if not tenant_id:
        return Response(
            ResponseData.error("Missing tenant_id"),
            status=status.HTTP_400_BAD_REQUEST
        )

    tenant = get_object_or_404(
        TenantDetailsModel,
        id=tenant_id,
        is_active=True
    )

    # select_related so we can read country.currency_symbol without extra queries
    payments = TenantPaymentModel.objects.filter(
        tenant=tenant,
        is_active=True,
        is_deleted=False
    ).select_related('country')\
     .order_by('-paid_at')

    # serialize exactly as before
    serializer = TenantPaymentSerializer(payments, many=True)
    serialized = serializer.data  # list of dicts

    # now combine amount + symbol into one field
    result = []
    for payment_obj, payment_dict in zip(payments, serialized):
        symbol = (
            payment_obj.country.currency_symbol
            if payment_obj.country else ''
        )
        # override the 'amount' field to include symbol
        payment_dict['amount'] = f"{payment_dict['amount']}{symbol}"
        result.append(payment_dict)

    return Response(
        ResponseData.success(result, "Payment history retrieved"),
        status=status.HTTP_200_OK
    )

    
@api_view(['POST'])
@authentication_classes([EnhancedJWTValidation, SessionAuthentication])
@permission_classes([IsAuthenticated])
def tenant_payment_is_active(request):
    """
    POST /api/payments/is_active/
    Body: { "tenant_id": <int>, "bed_id": <int> }

    Returns whether the tenant's subscription for that bed's country
    is still active (within 30 days). If not active or expired, includes
    the required currency symbol and amount to subscribe for that country,
    and marks the payment record inactive if it has expired.
    """
    # 1️⃣ Validate input
    print(f'request.datacc {request.data}')
    serializer = TenantSubscriptionStatusSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(
            ResponseData.error(serializer.errors),
            status=status.HTTP_400_BAD_REQUEST
        )

    tenant_id = serializer.validated_data['tenant_id']
    bed_id    = serializer.validated_data['bed_id']

    # 2️⃣ Fetch bed → country
    try:
        bed = LandlordRoomWiseBedModel.objects.select_related(
            'room__property__property_city__state__country'
        ).get(pk=bed_id)
    except LandlordRoomWiseBedModel.DoesNotExist:
        return Response(
            ResponseData.error(f"Bed with id={bed_id} not found"),
            status=status.HTTP_404_NOT_FOUND
        )
    # 3️⃣ Look for the most recent payment for this tenant & country
    last_payment = (
        TenantPaymentModel.objects
            .filter(
                tenant_id=tenant_id,
                country=bed.country,
                is_active=True,
                is_deleted=False,
            )
            .order_by('-paid_at')
            .first()
    )

    # Prepare fallback pricing info
    price  = bed.country.amount
    symbol = bed.country.currency_symbol or ''
    currency = bed.country.currency
    tenant = TenantDetailsModel.objects.filter(id=tenant_id).first()
    is_phone_verified = bool(tenant and tenant.phone_number)
    is_profile_pic_uploaded = bool(tenant and tenant.profile_picture)
    exists = TenantPersonalityDetailsModel.objects.filter(
        tenant_id=tenant_id,
        country__isnull=False,
        occupation__isnull=False,
        smoking_habit__isnull=False,
        drinking_habit__isnull=False,
        is_deleted=False
    ).exists()
    print(f'existsdddd {exists}')
    # 4️⃣ If no payment at all
    if not last_payment:
        return Response(
            ResponseData.success(
                {
                    "currency_symbol": symbol,
                    "currency" : currency,
                    'is_active' : False,
                    'is_phone_verified' : is_phone_verified,
                    'is_profile_pic_uploaded' : is_profile_pic_uploaded,
                    'is_required_personality_details_filled' : exists,
                    "amount": str(price) if price is not None else None
                },
                "No active subscription for this country",
            ),
            status=status.HTTP_200_OK
        )

    # 5️⃣ Check 30-day window on the found payment
    expiry = last_payment.paid_at + timedelta(days=30)
    if timezone.now() > expiry:
        # Mark this payment inactive in the database
        with transaction.atomic():
            last_payment.is_active = False
            last_payment.save(update_fields=['is_active'])

        return Response(
            ResponseData.success(
                
                {
                    "currency_symbol": symbol,
                    "currency" : currency,
                    'is_active' : False,
                    'is_phone_verified' : is_phone_verified,
                    'is_profile_pic_uploaded' : is_profile_pic_uploaded,
                    'is_required_personality_details_filled' : exists,
                    "amount": str(price) if price is not None else None,
                },
                "Subscription has expired for this country",
            ),
            status=status.HTTP_200_OK
        )

    # 6️⃣ Still active
    return Response(
        ResponseData.success(
            
            {
                'is_active' : True,
                'is_phone_verified' : is_phone_verified,
                'is_profile_pic_uploaded' : is_profile_pic_uploaded,
                'is_required_personality_details_filled' : exists,
                },
            "Subscription is active",
        ),
        status=status.HTTP_200_OK
    )