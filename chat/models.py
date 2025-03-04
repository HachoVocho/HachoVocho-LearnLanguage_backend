from django.db import models
from django.utils.timezone import now

class ChatMessageModel(models.Model):
    """
    Represents an individual chat message between a tenant and a landlord.
    
    The sender and receiver are stored as strings in the format "<role>:<id>".
    For example, "tenant:12" or "landlord:5".
    """
    sender = models.CharField(max_length=100)
    receiver = models.CharField(max_length=100)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    is_deleted = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Message from {self.sender} to {self.receiver}"

    def _parse_reference(self, reference):
        """
        Parse a reference string in the format "<role>:<id>".
        Returns a tuple of (role, pk).
        """
        try:
            role, pk = reference.split(":")
            return role, int(pk)
        except (ValueError, AttributeError):
            return None, None

    def get_sender_instance(self):
        """
        Resolve the sender reference to the corresponding model instance.
        """
        role, pk = self._parse_reference(self.sender)
        if role == "tenant":
            from tenant.models import TenantDetailsModel  # Replace 'your_app' with your app name
            return TenantDetailsModel.objects.filter(pk=pk).first()
        elif role == "landlord":
            from landlord.models import LandlordDetailsModel  # Replace 'your_app' with your app name
            return LandlordDetailsModel.objects.filter(pk=pk).first()
        return None

    def get_receiver_instance(self):
        """
        Resolve the receiver reference to the corresponding model instance.
        """
        role, pk = self._parse_reference(self.receiver)
        if role == "tenant":
            from tenant.models import TenantDetailsModel  # Replace 'your_app' with your app name
            return TenantDetailsModel.objects.filter(pk=pk).first()
        elif role == "landlord":
            from landlord.models import LandlordDetailsModel  # Replace 'your_app' with your app name
            return LandlordDetailsModel.objects.filter(pk=pk).first()
        return None
