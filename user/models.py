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
      
class OccupationModel(models.Model):
    title = models.CharField(max_length=20, unique=True)
    is_active = models.BooleanField(default=True)
    is_deleted = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=now)
    deleted_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.title
    
class ReligionModel(models.Model):
    title = models.CharField(max_length=20, unique=True)
    is_active = models.BooleanField(default=True)
    is_deleted = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=now)
    deleted_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.title
    
class IncomeRangeModel(models.Model):
    title = models.CharField(max_length=50, unique=True)  # Descriptive title like "Two-Figure Income"
    min_income = models.PositiveIntegerField(null=True, blank=True)  # Minimum income in the range
    max_income = models.PositiveIntegerField(null=True, blank=True)  # Maximum income in the range
    is_active = models.BooleanField(default=True)  # Active status
    is_deleted = models.BooleanField(default=False)  # Soft delete flag
    created_at = models.DateTimeField(default=now)  # Creation timestamp
    deleted_at = models.DateTimeField(null=True, blank=True)  # Deletion timestamp

    def __str__(self):
        return self.title
    
class SmokingHabitModel(models.Model):
    title = models.CharField(max_length=20, unique=True)
    is_active = models.BooleanField(default=True)
    is_deleted = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=now)
    deleted_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.title
    
class DrinkingHabitModel(models.Model):
    title = models.CharField(max_length=20, unique=True)
    is_active = models.BooleanField(default=True)
    is_deleted = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=now)
    deleted_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.title
    
class SocializingHabitModel(models.Model):
    title = models.CharField(max_length=20, unique=True)
    is_active = models.BooleanField(default=True)
    is_deleted = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=now)
    deleted_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.title
    
class RelationshipStatusModel(models.Model):
    title = models.CharField(max_length=20, unique=True)
    is_active = models.BooleanField(default=True)
    is_deleted = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=now)
    deleted_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.title
    
class FoodHabitModel(models.Model):
    title = models.CharField(max_length=20, unique=True)
    is_active = models.BooleanField(default=True)
    is_deleted = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=now)
    deleted_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.title
    

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