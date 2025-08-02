# models.py

from django.db import models
from django.utils.timezone import now
from landlord.models import LandlordRoomWiseBedModel
from tenant.models import TenantDetailsModel
from parler.models import TranslatableModel, TranslatedFields

class InterestRequestStatusModel(TranslatableModel):
    code = models.CharField(max_length=20, unique=True)  # e.g., 'pending', 'accepted'
    translations = TranslatedFields(
        label=models.CharField(max_length=50)
    )

    def __str__(self):
        return self.safe_translation_getter('label', any_language=True)
    
class TenantInterestRequestModel(models.Model):
    status = models.ForeignKey(InterestRequestStatusModel, on_delete=models.PROTECT, related_name="tenant_requests")
    tenant = models.ForeignKey(TenantDetailsModel, on_delete=models.CASCADE, related_name="tenant_interest_requests")
    bed = models.ForeignKey(LandlordRoomWiseBedModel, on_delete=models.CASCADE, related_name="tenant_interest_requests_for_bed", null=False, default='')
    landlord_message = models.CharField(max_length=50, default='', blank=True)
    request_closed_by = models.CharField(max_length=50, default='', blank=True)
    created_at = models.DateTimeField(default=now)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    is_deleted = models.BooleanField(default=False)

    def set_status(self, code, lang='en'):
        self.status = InterestRequestStatusModel.objects.language(lang).get(code=code)
        self.save()

    def accept(self):
        self.status = InterestRequestStatusModel.objects.get(code='accepted')
        self.save()

    def reject(self):
        self.status = InterestRequestStatusModel.objects.get(code='rejected')
        self.save()

    def close(self, lang='en'):
        self.set_status('closed', lang)

    def __str__(self):
        return f"Tenant: {self.tenant.email} - Bed: {self.bed.bed_number} - Status: {self.status}"

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["tenant", "bed"],
                condition=Q(is_active=True, is_deleted=False),
                name="unique_active_tenant_bed_request"
            )
        ]
        
class LandlordInterestRequestModel(models.Model):
    status = models.ForeignKey(InterestRequestStatusModel, on_delete=models.PROTECT, related_name="landlord_requests")
    tenant = models.ForeignKey(TenantDetailsModel, on_delete=models.CASCADE, related_name="landlord_interest_requests")
    bed = models.ForeignKey(LandlordRoomWiseBedModel, on_delete=models.CASCADE, related_name="landlord_interest_requests_from_bed", null=False, default='')
    tenant_message = models.CharField(max_length=50, default='', blank=True)
    request_closed_by = models.CharField(max_length=50, default='', blank=True)
    created_at = models.DateTimeField(default=now)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    is_deleted = models.BooleanField(default=False)

    def set_status(self, code, lang='en'):
        self.status = InterestRequestStatusModel.objects.language(lang).get(code=code)
        self.save()

    def accept(self, lang='en'):
        self.set_status('accepted', lang)

    def reject(self, lang='en'):
        self.set_status('rejected', lang)

    def close(self, lang='en'):
        self.set_status('closed', lang)

    def __str__(self):
        return f"Landlord: {self.bed.room.property.landlord.first_name} - Tenant: {self.tenant.email} - Status: {self.status}"
