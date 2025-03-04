# payments/serializers.py
from rest_framework import serializers
from .models import TenantPaymentModel
from tenant.models import TenantDetailsModel

class TenantPaymentSerializer(serializers.ModelSerializer):
    tenant = serializers.PrimaryKeyRelatedField(
        queryset=TenantDetailsModel.objects.filter(is_active=True),
        help_text="ID of the tenant making the payment"
    )

    class Meta:
        model = TenantPaymentModel
        fields = (
            'tenant',
            'payment_method',
            'amount',
            'transaction_id',
            'status',
        )
        read_only_fields = ('transaction_id', 'status')
