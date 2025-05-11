# payments/views.py
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status

from payments.models import TenantPaymentModel
from tenant.models import TenantDetailsModel
from .serializers import TenantPaymentSerializer
from response import Response as ResponseData
from user.authentication import EnhancedJWTValidation
from rest_framework.permissions import IsAuthenticated  # Adjust import according to your project structure
from django.conf import settings
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
import braintree
from rest_framework.permissions import AllowAny
from rest_framework.authentication import SessionAuthentication
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
                transaction_id=transaction.id,
                status=transaction.status
            )

            return Response(
                ResponseData.success_without_data("Transaction successful"),
                status=status.HTTP_200_OK
            )
        else:
            return Response(
                ResponseData.error("Transaction failed", result.message),
                status=status.HTTP_400_BAD_REQUEST
            )
    except Exception as e:
        return Response(
            ResponseData.error("Error processing payment", str(e)),
            status=status.HTTP_400_BAD_REQUEST
        )

    
@api_view(['POST'])
def tenant_payment_history(request):
    """
    POST /api/payments/history/
    Body: { "tenant_id": <integer> }

    Returns all non-deleted payments for the given tenant, newest first.
    """
    tenant_id = request.data.get('tenant_id')
    if not tenant_id:
        return Response(
            ResponseData.error("Missing tenant_id"),
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        tenant = TenantDetailsModel.objects.get(id=tenant_id, is_active=True)
    except TenantDetailsModel.DoesNotExist:
        return Response(
            ResponseData.error("Tenant not found"),
            status=status.HTTP_404_NOT_FOUND
        )

    payments = TenantPaymentModel.objects.filter(
        tenant=tenant,
        is_active=True,
        is_deleted=False
    ).order_by('-paid_at')

    serializer = TenantPaymentSerializer(payments, many=True)
    return Response(
        ResponseData.success(serializer.data, "Payment history retrieved"),
        status=status.HTTP_200_OK
    )