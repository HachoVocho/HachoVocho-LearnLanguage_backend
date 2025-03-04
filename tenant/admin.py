from django.contrib import admin
from .models import (
    TenantDetailsModel,
    TenantEmailVerificationModel,
    TenantIdentityVerificationFile,
    TenantPersonalityDetailsModel,
    TenantDocumentTypeModel,
    TenantIdentityVerificationModel,
    TenantPreferenceQuestionTypeModel,
    TenantPreferenceQuestionModel,
    TenantPreferenceOptionModel,
    TenantPreferenceAnswerModel,
)

@admin.register(TenantDetailsModel)
class TenantDetailsAdmin(admin.ModelAdmin):
    list_display = ('id', 'first_name', 'last_name', 'email', 'preferred_city', 'is_active', 'created_at')
    search_fields = ('email', 'first_name', 'last_name')
    list_filter = ('is_active', 'is_deleted')
    readonly_fields = ('created_at', 'deleted_at')


@admin.register(TenantEmailVerificationModel)
class TenantEmailVerificationModelAdmin(admin.ModelAdmin):
    list_display = ('tenant', 'otp', 'is_verified')
    search_fields = ('tenant__email',)
    list_filter = ('is_verified', 'created_at')
    readonly_fields = ('created_at',)


@admin.register(TenantPreferenceQuestionTypeModel)
class TenantPreferenceQuestionTypeModelAdmin(admin.ModelAdmin):
    list_display = ('type_name', 'description', 'is_active')
    list_filter = ('is_active', 'is_deleted', 'created_at')
    readonly_fields = ('created_at', 'deleted_at')


@admin.register(TenantPreferenceQuestionModel)
class TenantPreferenceQuestionModelAdmin(admin.ModelAdmin):
    list_display = ('id', 'question_text', 'question_type')
    search_fields = ('question_text',)
    readonly_fields = ('created_at', 'deleted_at')


@admin.register(TenantPreferenceOptionModel)
class TenantPreferenceOptionModelAdmin(admin.ModelAdmin):
    list_display = ('id', 'question', 'option_text')
    search_fields = ('question__question_text', 'option_text')
    readonly_fields = ('created_at', 'deleted_at')


@admin.register(TenantPreferenceAnswerModel)
class TenantPreferenceAnswerModelAdmin(admin.ModelAdmin):
    list_display = (
        'tenant', 
        'question', 
        'option', 
        'priority', 
        'static_option', 
        'is_active', 
        'created_at'
    )
    list_filter = ('is_active', 'is_deleted', 'created_at')
    search_fields = ('tenant__email', 'question__question_text', 'option__option_text')
    ordering = ('-created_at',)
    readonly_fields = ('created_at', 'deleted_at')


@admin.register(TenantPersonalityDetailsModel)
class TenantPersonalityDetailsModelAdmin(admin.ModelAdmin):
    list_display = (
        'tenant', 
        'occupation', 
        'country', 
        'religion', 
        'income_range', 
        'smoking_habit', 
        'drinking_habit', 
        'socializing_habit', 
        'relationship_status', 
        'food_habit', 
        'pet_lover', 
        'is_active', 
        'created_at'
    )
    list_filter = ('is_active', 'is_deleted', 'created_at')
    search_fields = ('tenant__email', 'occupation__title', 'religion__title', 'country__name')
    ordering = ('-created_at',)
    readonly_fields = ('created_at', 'deleted_at')


@admin.register(TenantDocumentTypeModel)
class TenantDocumentTypeModelAdmin(admin.ModelAdmin):
    list_display = ('id', 'type_name', 'description', 'is_active', 'created_at')
    list_filter = ('is_active', 'is_deleted', 'created_at')
    search_fields = ('type_name',)
    ordering = ('-created_at',)
    readonly_fields = ('created_at', 'deleted_at')


@admin.register(TenantIdentityVerificationModel)
class TenantIdentityVerificationModelAdmin(admin.ModelAdmin):
    list_display = ('tenant', 'document_type', 'document_number', 'verification_status', 'submitted_at')
    list_filter = ('verification_status', 'is_active', 'is_deleted', 'submitted_at')
    search_fields = ('tenant__email', 'document_number')
    ordering = ('-submitted_at',)
    readonly_fields = ('submitted_at', 'verified_at', 'created_at', 'deleted_at')

@admin.register(TenantIdentityVerificationFile)
class TenantIdentityVerificationFileAdmin(admin.ModelAdmin):
    list_display = ('id', 'identity_document', 'file', 'uploaded_at')
    list_filter = ('uploaded_at',)
    search_fields = ('identity_document__tenant__email', 'file')
    ordering = ('-uploaded_at',)
