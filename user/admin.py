from django.contrib import admin
from .models import (
    OTPModel,
    UserRoleModel,
    OccupationModel,
    ReligionModel,
    IncomeRangeModel,
    SmokingHabitModel,
    DrinkingHabitModel,
    SocializingHabitModel,
    RelationshipStatusModel,
    FoodHabitModel,
)
from parler.admin import TranslatableAdmin
@admin.register(UserRoleModel)
class UserRoleModelAdmin(admin.ModelAdmin):
    """
    Custom admin class to manage user roles.
    """
    list_display = ('id', 'role_name', 'is_active', 'created_at')  # Columns displayed in admin
    search_fields = ('role_name',)  # Search functionality
    list_filter = ('is_active', 'is_deleted')  # Filters for the sidebar
    readonly_fields = ('created_at', 'deleted_at')  # Fields that are read-only

@admin.register(OccupationModel)
class OccupationModelAdmin(TranslatableAdmin):
    """
    Custom admin class to manage occupation options.
    """
    list_display = ('id', 'title', 'is_active', 'created_at')  # Columns displayed in admin
    search_fields = ('title',)  # Search functionality
    list_filter = ('is_active', 'is_deleted')  # Filters for the sidebar
    readonly_fields = ('created_at', 'deleted_at')  # Fields that are read-only

@admin.register(ReligionModel)
class ReligionModelAdmin(TranslatableAdmin):
    """
    Custom admin class to manage religion options.
    """
    list_display = ('id', 'title', 'is_active', 'created_at')  # Columns displayed in admin
    search_fields = ('title',)  # Search functionality
    list_filter = ('is_active', 'is_deleted')  # Filters for the sidebar
    readonly_fields = ('created_at', 'deleted_at')  # Fields that are read-only

@admin.register(IncomeRangeModel)
class IncomeRangeModelAdmin(TranslatableAdmin):
    """
    Custom admin class to manage income range options.
    """
    list_display = ('id', 'title', 'min_income', 'max_income', 'is_active', 'created_at')  # Columns displayed in admin
    search_fields = ('title',)  # Search functionality
    list_filter = ('is_active', 'is_deleted')  # Filters for the sidebar
    readonly_fields = ('created_at', 'deleted_at')  # Fields that are read-only

@admin.register(SmokingHabitModel)
class SmokingHabitModelAdmin(TranslatableAdmin):
    """
    Custom admin class to manage smoking habit options.
    """
    list_display = ('id', 'title', 'is_active', 'created_at')  # Columns displayed in admin
    search_fields = ('title',)  # Search functionality
    list_filter = ('is_active', 'is_deleted')  # Filters for the sidebar
    readonly_fields = ('created_at', 'deleted_at')  # Fields that are read-only

@admin.register(DrinkingHabitModel)
class DrinkingHabitModelAdmin(TranslatableAdmin):
    """
    Custom admin class to manage drinking habit options.
    """
    list_display = ('id', 'title', 'is_active', 'created_at')  # Columns displayed in admin
    search_fields = ('title',)  # Search functionality
    list_filter = ('is_active', 'is_deleted')  # Filters for the sidebar
    readonly_fields = ('created_at', 'deleted_at')  # Fields that are read-only

@admin.register(SocializingHabitModel)
class SocializingHabitModelAdmin(TranslatableAdmin):
    """
    Custom admin class to manage socializing habit options.
    """
    list_display = ('id', 'title', 'is_active', 'created_at')  # Columns displayed in admin
    search_fields = ('title',)  # Search functionality
    list_filter = ('is_active', 'is_deleted')  # Filters for the sidebar
    readonly_fields = ('created_at', 'deleted_at')  # Fields that are read-only

@admin.register(RelationshipStatusModel)
class RelationshipStatusModelAdmin(TranslatableAdmin):
    """
    Custom admin class to manage relationship status options.
    """
    list_display = ('id', 'title', 'is_active', 'created_at')  # Columns displayed in admin
    search_fields = ('title',)  # Search functionality
    list_filter = ('is_active', 'is_deleted')  # Filters for the sidebar
    readonly_fields = ('created_at', 'deleted_at')  # Fields that are read-only

@admin.register(FoodHabitModel)
class FoodHabitModelAdmin(TranslatableAdmin):
    """
    Custom admin class to manage food habit options.
    """
    list_display = ('id', 'title', 'is_active', 'created_at')  # Columns displayed in admin
    search_fields = ('title',)  # Search functionality
    list_filter = ('is_active', 'is_deleted')  # Filters for the sidebar
    readonly_fields = ('created_at', 'deleted_at')  # Fields that are read-only

@admin.register(OTPModel)
class OTPModelAdmin(admin.ModelAdmin):
    list_display = ('phone_number', 'otp', 'role_name', 'is_verified', 'created_at', 'verified_at')
    search_fields = ('phone_number', 'otp', 'role_name')
    list_filter = ('role_name', 'is_verified')
    readonly_fields = ('created_at', 'verified_at')