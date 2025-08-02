from django.contrib import admin
from django.contrib.contenttypes.admin import GenericTabularInline
from .models import (
    LandlordBasePreferenceModel,
    LandlordDetailsModel,
    LandlordEmailVerificationModel,
    LandlordPropertyTypeModel,
    LandlordPropertyAmenityModel,
    LandlordPropertyDetailsModel,
    LandlordPropertyRoomTypeModel,
    LandlordPropertyRoomDetailsModel,
    LandlordRoomWiseBedModel,
    LandlordQuestionTypeModel,
    LandlordQuestionModel,
    LandlordOptionModel,
    LandlordAnswerModel,
    LandlordDocumentTypeModel,
    LandlordIdentityVerificationModel,
    LandlordPropertyVerificationModel,
)

from .models import LandlordBedMediaModel, LandlordRoomMediaModel, LandlordPropertyMediaModel
from parler.admin import TranslatableAdmin
@admin.register(LandlordBedMediaModel)
class LandlordBedMediaModelAdmin(admin.ModelAdmin):
    list_display = ('bed', 'media_type', 'is_active', 'is_deleted')
    list_filter = ('media_type', 'is_active', 'is_deleted')
    search_fields = ('bed__id',)  # Search by bed ID

@admin.register(LandlordRoomMediaModel)
class LandlordRoomMediaModelAdmin(admin.ModelAdmin):
    list_display = ('room', 'media_type', 'is_active', 'is_deleted')
    list_filter = ('media_type', 'is_active', 'is_deleted')
    search_fields = ('room__id',)  # Search by room ID

@admin.register(LandlordPropertyMediaModel)
class LandlordPropertyMediaModelAdmin(admin.ModelAdmin):
    list_display = ('property', 'media_type', 'is_active', 'is_deleted')
    list_filter = ('media_type', 'is_active', 'is_deleted')
    search_fields = ('property__id',)  # Search by property ID
    
@admin.register(LandlordDetailsModel)
class LandlordDetailsAdmin(admin.ModelAdmin):
    list_display = ('id', 'first_name', 'last_name', 'email', 'is_active', 'created_at')
    search_fields = ('email', 'first_name', 'last_name')
    list_filter = ('is_active', 'is_deleted')
    readonly_fields = ('created_at', 'deleted_at')

@admin.register(LandlordEmailVerificationModel)
class LandlordEmailVerificationModelAdmin(admin.ModelAdmin):
    list_display = ('id', 'landlord', 'otp', 'is_verified')

@admin.register(LandlordPropertyTypeModel)
class LandlordPropertyTypeModelAdmin(TranslatableAdmin):
    list_display = ('type_name', 'is_active', 'is_deleted', 'created_at', 'deleted_at')
    list_filter = ('is_active', 'is_deleted', 'created_at')
    search_fields = ('type_name', 'description')
    readonly_fields = ('created_at', 'deleted_at')
    ordering = ('-created_at',)

@admin.register(LandlordPropertyAmenityModel)
class LandlordPropertyAmenityModelAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_active', 'is_deleted', 'created_at', 'deleted_at')
    list_filter = ('is_active', 'is_deleted', 'created_at')
    search_fields = ('name', 'description')
    readonly_fields = ('created_at', 'deleted_at')
    ordering = ('-created_at',)

@admin.register(LandlordPropertyDetailsModel)
class   Admin(admin.ModelAdmin):
    list_display = ('id','street_number','longitude','latitude','property_city','property_city_id','property_name', 'property_address', 'property_size','pin_code', 'property_type', 'number_of_rooms', 'is_active')
    list_filter = ('is_active', 'is_deleted', 'created_at')
    search_fields = ('property_name', 'property_address')
    readonly_fields = ('created_at', 'deleted_at')
    ordering = ('-created_at',)

@admin.register(LandlordPropertyRoomTypeModel)
class LandlordPropertyRoomTypeModelAdmin(admin.ModelAdmin):
    list_display = ('type_name', 'description', 'is_active', 'created_at')
    list_filter = ('is_active', 'is_deleted', 'created_at')
    search_fields = ('type_name',)
    readonly_fields = ('created_at', 'deleted_at')
    ordering = ('-created_at',)

@admin.register(LandlordPropertyRoomDetailsModel)
class LandlordPropertyRoomDetailsModelAdmin(admin.ModelAdmin):
    list_display = ('current_female_occupants','current_male_occupants','id','property', 'room_size', 'room_type', 'number_of_beds', 'number_of_windows', 'max_people_allowed', 'floor')
    list_filter = ('is_active', 'is_deleted', 'created_at')
    search_fields = ('room_size',)
    readonly_fields = ('created_at', 'deleted_at')
    ordering = ('-created_at',)

@admin.register(LandlordRoomWiseBedModel)
class LandlordRoomWiseBedModelAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'room',
        'property_id',           # ← our new column
        'bed_number',
        'availability_start_date',
        'is_active',
    )
    list_filter = ('is_active', 'is_deleted', 'created_at')
    search_fields = ('bed_number',)
    readonly_fields = ('created_at', 'deleted_at')
    ordering = ('-created_at',)

    def property_id(self, obj):
        # obj.room is the ForeignKey to LandlordPropertyRoomDetailsModel
        # that has its own `.property` FK to LandlordPropertyDetailsModel
        return obj.room.property.id
    property_id.short_description = "Property ID"


@admin.register(LandlordQuestionTypeModel)
class LandlordQuestionTypeModelAdmin(admin.ModelAdmin):
    list_display = ('id', 'type_name', 'QUESTION_TYPES', 'is_active')
    list_filter = ('is_active', 'is_deleted', 'created_at')
    readonly_fields = ('created_at', 'deleted_at')

@admin.register(LandlordQuestionModel)
class LandlordQuestionModelAdmin(TranslatableAdmin):
    list_display = ('id', 'question_type')
    readonly_fields = ('created_at', 'deleted_at')

@admin.register(LandlordOptionModel)
class LandlordOptionModelAdmin(TranslatableAdmin):
    list_display = ('id', 'question')
    readonly_fields = ('created_at', 'deleted_at')

@admin.register(LandlordAnswerModel)    
class LandlordAnswerModelAdmin(admin.ModelAdmin):
    list_display = ('id', 'question', 'content_type', 'object_id', 'preference')
    list_filter = ('is_active', 'is_deleted', 'created_at')
    readonly_fields = ('created_at', 'deleted_at')

@admin.register(LandlordDocumentTypeModel)
class LandlordPropertyVerificationDocumentTypeModelAdmin(admin.ModelAdmin):
    list_display = ('type_name', 'description', 'is_active', 'created_at')
    list_filter = ('is_active', 'is_deleted', 'created_at')
    search_fields = ('type_name', 'description')
    readonly_fields = ('created_at', 'deleted_at')

@admin.register(LandlordIdentityVerificationModel)
class LandlordIdentityVerificationModelAdmin(admin.ModelAdmin):
    list_display = ('landlord', 'document_type', 'document_number', 'verification_status', 'submitted_at')
    list_filter = ('verification_status', 'is_active', 'created_at')
    search_fields = ('document_number',)
    readonly_fields = ('submitted_at', 'verified_at', 'created_at', 'deleted_at')

@admin.register(LandlordPropertyVerificationModel)
class LandlordPropertyVerificationModelAdmin(admin.ModelAdmin):
    list_display = ('property', 'document_type', 'verification_status', 'furnishing_status', 'submitted_at')
    list_filter = ('verification_status', 'is_active', 'created_at')
    search_fields = ('property__property_name',)
    readonly_fields = ('submitted_at', 'verified_at', 'created_at', 'deleted_at')

class BasePreferenceAnswerInline(admin.TabularInline):
    """
    Inline for the LandlordBasePreferenceModel.answers ManyToMany field.
    """
    model = LandlordBasePreferenceModel.answers.through
    extra = 1
    verbose_name = "Answer"
    verbose_name_plural = "Answers"

@admin.register(LandlordBasePreferenceModel)
class LandlordBasePreferenceAdmin(admin.ModelAdmin):
    list_display = (
        'landlord',
        'answer_count',
        'created_at',
        'updated_at',
    )
    list_filter = ('created_at', 'updated_at')
    search_fields = ('landlord__email', 'landlord__first_name', 'landlord__last_name')
    inlines = (BasePreferenceAnswerInline,)
    readonly_fields = ('created_at', 'updated_at')

    def answer_count(self, obj):
        return obj.answers.count()
    answer_count.short_description = 'Number of Answers'
