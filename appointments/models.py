# appointments/models.py

from django.db import models
from django.utils.timezone import now
from parler.models import TranslatableModel, TranslatedFields
from landlord.models import LandlordDetailsModel, LandlordRoomWiseBedModel
from landlord_availability.models import LandlordAvailabilitySlotModel
from tenant.models import TenantDetailsModel
from parler.models import TranslatableModel, TranslatedFields

class AppointmentStatusModel(TranslatableModel):
    code = models.CharField(max_length=20, unique=True)  # e.g., "pending"
    translations = TranslatedFields(
        label = models.CharField(max_length=50)
    )

    def __str__(self):
        return self.safe_translation_getter('label', any_language=True)
    
class AppointmentBookingModel(TranslatableModel):
    tenant      = models.ForeignKey(TenantDetailsModel,      on_delete=models.CASCADE, related_name='tenant_appointments')
    landlord    = models.ForeignKey(LandlordDetailsModel,    on_delete=models.CASCADE, related_name='landlord_appointments')
    bed         = models.ForeignKey(LandlordRoomWiseBedModel, on_delete=models.CASCADE, related_name='bed_appointments')
    time_slot   = models.ForeignKey(LandlordAvailabilitySlotModel, on_delete=models.CASCADE, related_name='slot_appointments')

    status = models.ForeignKey(AppointmentStatusModel, on_delete=models.PROTECT, related_name='appointments')
    INITIATED_BY_CHOICES = [('tenant','Tenant'),('landlord','Landlord')]
    initiated_by   = models.CharField(max_length=10, choices=INITIATED_BY_CHOICES, default='tenant')
    last_updated_by= models.CharField(max_length=10, choices=INITIATED_BY_CHOICES, default='tenant')

    is_active   = models.BooleanField(default=True)
    is_deleted  = models.BooleanField(default=False)
    created_at  = models.DateTimeField(default=now)
    updated_at  = models.DateTimeField(auto_now=True)

    # <-- only this TranslatedFields block is needed -->
    translations = TranslatedFields(
        title = models.CharField(max_length=50, help_text="Translated human‑readable status")
    )

    class Meta:
        verbose_name = "Appointment Booking"
        verbose_name_plural = "Appointment Bookings"
        ordering = ['-created_at']

    def __str__(self):
        return f"Appointment #{self.id} – {self.tenant} & {self.landlord} ({self.status})"
