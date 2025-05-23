# payments/models.py
from django.db import models
from django.conf import settings

from localization.models import CountryModel
from tenant.models import TenantDetailsModel

class TenantPaymentModel(models.Model):
    tenant = models.ForeignKey(TenantDetailsModel, on_delete=models.CASCADE, related_name='tenant_payment')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    country = models.ForeignKey(
        CountryModel,
        on_delete=models.PROTECT,
        related_name='tenant_payments',
        null=True,
        blank=True,
        help_text="Country whose pricing was used for this payment"
    )
    paid_at = models.DateTimeField(auto_now_add=True)
    transaction_id = models.CharField(max_length=255, blank=True, null=True)
    status = models.CharField(max_length=50, default='pending')
    is_active = models.BooleanField(default=True)
    is_deleted = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.tenant} - {self.amount}"
