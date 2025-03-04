# payments/models.py
from django.db import models
from django.conf import settings

from tenant.models import TenantDetailsModel

class TenantPaymentModel(models.Model):
    tenant = models.ForeignKey(TenantDetailsModel, on_delete=models.CASCADE, related_name='tenant_payment')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    paid_at = models.DateTimeField(auto_now_add=True)
    transaction_id = models.CharField(max_length=255, blank=True, null=True)
    status = models.CharField(max_length=50, default='pending')
    is_active = models.BooleanField(default=True)
    is_deleted = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.tenant} - {self.amount}"
