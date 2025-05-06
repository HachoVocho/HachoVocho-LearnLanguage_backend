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

class TenantPaymentSerializer(serializers.ModelSerializer):
    status = serializers.SerializerMethodField()
    paid_at = serializers.SerializerMethodField()

    class Meta:
        model = TenantPaymentModel
        fields = [
            'id',
            'amount',
            'paid_at',
            'transaction_id',
            'status',
        ]
        read_only_fields = fields

    def get_status(self, obj):
        if obj.status == 'submitted_for_settlement':
            return 'Paid'
        return obj.status

    def get_paid_at(self, obj):
        dt = obj.paid_at
        # Day with ordinal suffix
        day = dt.day
        if 11 <= day <= 13:
            suffix = 'th'
        else:
            suffix = {1: 'st', 2: 'nd', 3: 'rd'}.get(day % 10, 'th')
        day_str = f"{day}{suffix}"

        # Month full name
        month_str = dt.strftime('%B')  # e.g. 'July'

        # Year
        year_str = dt.year

        # Time in 12-hour with AM/PM
        time_str = dt.strftime('%-I:%M %p')  # e.g. '6:54 PM'

        return f"{day_str} {month_str} {year_str}, {time_str}"