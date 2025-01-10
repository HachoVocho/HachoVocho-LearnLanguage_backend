from django.db import models
from django.utils.timezone import now

class UserRoleModel(models.Model):
    ROLE_CHOICES = [
        ('tenant', 'Tenant'),
        ('landlord', 'Landlord'),
    ]
    role_name = models.CharField(max_length=20, choices=ROLE_CHOICES, unique=True)
    is_active = models.BooleanField(default=True)
    is_deleted = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=now)
    deleted_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.role_name
      