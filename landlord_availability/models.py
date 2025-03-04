from django.db import models
from django.utils.timezone import now
from landlord.models import LandlordDetailsModel, LandlordPropertyDetailsModel

class LandlordAvailabilityModel(models.Model):
    """
    Model to store availability of landlords for each property.
    """
    landlord = models.ForeignKey(LandlordDetailsModel, on_delete=models.CASCADE, related_name='landlord_availabilities')
    property = models.ForeignKey(LandlordPropertyDetailsModel, on_delete=models.CASCADE, related_name='property_availabilities')
    date = models.DateField()  # Availability for a particular date
    is_active = models.BooleanField(default=True)
    is_deleted = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('landlord', 'property', 'date')  # Ensure unique availability per property & date

    def __str__(self):
        return f"Availability for {self.property.property_name} on {self.date}"


class LandlordAvailabilitySlotModel(models.Model):
    """
    Model to store specific time slots on a given availability date.
    """
    availability = models.ForeignKey(LandlordAvailabilityModel, on_delete=models.CASCADE, related_name='time_slots')
    start_time = models.TimeField()
    end_time = models.TimeField()
    is_active = models.BooleanField(default=True)
    is_deleted = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=now)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Slot: {self.start_time} - {self.end_time}"

