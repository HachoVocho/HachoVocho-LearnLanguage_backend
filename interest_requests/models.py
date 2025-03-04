from django.db import models
from django.utils.timezone import now
from landlord.models import LandlordRoomWiseBedModel
from tenant.models import TenantDetailsModel

# Create your models here.
class TenantInterestRequestModel(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('accepted', 'Accepted'),
        ('rejected', 'Rejected'),
        ('closed', 'Closed'),
    ]

    tenant = models.ForeignKey(TenantDetailsModel, on_delete=models.CASCADE, related_name="tenant_interest_requests") # Tenant who is interested
    bed = models.ForeignKey(LandlordRoomWiseBedModel, on_delete=models.CASCADE, related_name="tenant_interest_requests_for_bed",null=False,default='') # Property they are interested in
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending') # Status of request
    landlord_message = models.CharField(max_length=50, default='',blank=True) # Status of request
    request_closed_by = models.CharField(max_length=50, default='',blank=True) # Status of request
    created_at = models.DateTimeField(default=now) # When request was made
    updated_at = models.DateTimeField(auto_now=True) # Last status update
    is_active = models.BooleanField(default=True)
    is_deleted = models.BooleanField(default=False)

    def accept(self):
        """Method to accept interest request"""
        self.status = 'accepted'
        self.save()

    def reject(self):
        """Method to reject interest request"""
        self.status = 'rejected'
        self.save()

    def close(self):
        """Method to block the user who sent request"""
        self.status = 'closed'
        self.save()

    def __str__(self):
        return f"Tenant: {self.tenant.email} - Property: {self.bed.bed_number} - Status: {self.status}"
    
class LandlordInterestRequestModel(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('accepted', 'Accepted'),
        ('rejected', 'Rejected'),
        ('closed', 'Closed'),
    ]

    tenant = models.ForeignKey(TenantDetailsModel, on_delete=models.CASCADE, related_name="landlord_interest_requests")  # Tenant who is interested
    bed = models.ForeignKey(LandlordRoomWiseBedModel, on_delete=models.CASCADE, related_name="landlord_interest_requests_from_bed",null=False,default='')  # Property they are interested in
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')  # Status of request
    tenant_message = models.CharField(max_length=50, default='',blank=True)  # Status of request
    request_closed_by = models.CharField(max_length=50, default='',blank=True) # Status of request
    created_at = models.DateTimeField(default=now)  # When request was made
    updated_at = models.DateTimeField(auto_now=True)  # Last status update
    is_active = models.BooleanField(default=True)
    is_deleted = models.BooleanField(default=False)

    def accept(self):
        """Method to accept interest request"""
        self.status = 'accepted'
        self.save()

    def reject(self):
        """Method to reject interest request"""
        self.status = 'rejected'
        self.save()

    def close(self):
        """Method to block the user who sent request"""
        self.status = 'closed'
        self.save()

    def __str__(self):
        return f"Landlord: {self.bed.room.property.landlord.first_name} - Tenant: {self.tenant.email} - Status: {self.status}"