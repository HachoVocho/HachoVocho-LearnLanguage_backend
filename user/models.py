from django.db import models
from django.utils.timezone import now
from parler.models import TranslatableModel, TranslatedFields

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
      
class OccupationModel(TranslatableModel):
    translations = TranslatedFields(
        title = models.CharField(max_length=50),
    )
    is_active = models.BooleanField(default=True)
    is_deleted = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=now)
    deleted_at = models.DateTimeField(null=True, blank=True)

    
class ReligionModel(TranslatableModel):
    translations = TranslatedFields(
        title = models.CharField(max_length=50),
    )
    is_active = models.BooleanField(default=True)
    is_deleted = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=now)
    deleted_at = models.DateTimeField(null=True, blank=True)

    
class IncomeRangeModel(TranslatableModel):
    translations = TranslatedFields(
        title = models.CharField(max_length=50),
    )
    min_income = models.PositiveIntegerField(null=True, blank=True)  # Minimum income in the range
    max_income = models.PositiveIntegerField(null=True, blank=True)  # Maximum income in the range
    is_active = models.BooleanField(default=True)  # Active status
    is_deleted = models.BooleanField(default=False)  # Soft delete flag
    created_at = models.DateTimeField(default=now)  # Creation timestamp
    deleted_at = models.DateTimeField(null=True, blank=True)  # Deletion timestamp

    
class SmokingHabitModel(TranslatableModel):
    translations = TranslatedFields(
        title = models.CharField(max_length=50),
    )
    is_active = models.BooleanField(default=True)
    is_deleted = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=now)
    deleted_at = models.DateTimeField(null=True, blank=True)

     
class DrinkingHabitModel(TranslatableModel):
    translations = TranslatedFields(
        title = models.CharField(max_length=50),
    )
    is_active = models.BooleanField(default=True)
    is_deleted = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=now)
    deleted_at = models.DateTimeField(null=True, blank=True)

    
class SocializingHabitModel(TranslatableModel):
    translations = TranslatedFields(
        title = models.CharField(max_length=50),
    )
    is_active = models.BooleanField(default=True)
    is_deleted = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=now)
    deleted_at = models.DateTimeField(null=True, blank=True)

    
class RelationshipStatusModel(TranslatableModel):
    translations = TranslatedFields(
        title = models.CharField(max_length=50),
    )
    is_active = models.BooleanField(default=True)
    is_deleted = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=now)
    deleted_at = models.DateTimeField(null=True, blank=True)

    
class FoodHabitModel(TranslatableModel):
    translations = TranslatedFields(
        title = models.CharField(max_length=50),
    )
    is_active = models.BooleanField(default=True)
    is_deleted = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=now)
    deleted_at = models.DateTimeField(null=True, blank=True)

    

class OTPModel(models.Model):
    ROLE_CHOICES = [
        ('tenant', 'Tenant'),
        ('landlord', 'Landlord'),
    ]
    role_name = models.CharField(max_length=20, choices=ROLE_CHOICES, unique=False)
    phone_number = models.CharField(max_length=15, unique=True)
    otp = models.CharField(max_length=6)
    is_verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=now)
    verified_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.phone_number} - {self.otp}"