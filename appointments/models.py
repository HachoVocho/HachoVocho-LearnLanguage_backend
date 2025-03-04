from django.db import models
from django.utils.timezone import now
from landlord.models import LandlordDetailsModel, LandlordRoomWiseBedModel
from landlord_availability.models import LandlordAvailabilitySlotModel
from tenant.models import TenantDetailsModel

class AppointmentBookingModel(models.Model):
    """
    Model to store information about appointments between tenants and landlords
    """
    tenant = models.ForeignKey(
        TenantDetailsModel,
        on_delete=models.CASCADE,
        related_name='tenant_appointments'
    )
    landlord = models.ForeignKey(
        LandlordDetailsModel,
        on_delete=models.CASCADE,
        related_name='landlord_appointments'
    )
    bed = models.ForeignKey(
        LandlordRoomWiseBedModel,
        on_delete=models.CASCADE,
        related_name='bed_appointments'
    )
    time_slot = models.ForeignKey(
        LandlordAvailabilitySlotModel,
        on_delete=models.CASCADE,
        related_name='slot_appointments'
    )
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('cancelled', 'Cancelled'),
        ('completed', 'Completed'),
    ]
    
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending'
    )

    # New field to track who initiated the request
    INITIATED_BY_CHOICES = [
        ('tenant', 'Tenant'),
        ('landlord', 'Landlord'),
    ]
    initiated_by = models.CharField(
        max_length=10,
        choices=INITIATED_BY_CHOICES,
        default='tenant'
    )

    # Audit fields
    is_active = models.BooleanField(default=True)
    is_deleted = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Appointment Booking"
        verbose_name_plural = "Appointment Bookings"
        ordering = ['-created_at']

    def __str__(self):
        return f"Appointment #{self.id} - {self.tenant} & {self.landlord} ({self.status})"