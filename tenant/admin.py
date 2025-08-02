from django.contrib import admin

from localization.models import CityModel
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
from parler.admin import TranslatableAdmin

@admin.register(TenantDetailsModel)
class TenantDetailsAdmin(admin.ModelAdmin):
    list_display = (
        'id','first_name','last_name','email','preferred_city',
        'phone_number','is_active','created_at'
    )
    list_filter = ('is_active','is_deleted')
    search_fields = ('email','first_name','last_name')

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "preferred_city":
            # Grab the first 10 for browsing…
            base_qs = CityModel.objects.all()[:10]

            # But if we’re editing an existing Tenant, make sure their city is included
            obj_id = request.resolver_match.kwargs.get('object_id')
            if obj_id:
                try:
                    tenant = TenantDetailsModel.objects.get(pk=obj_id)
                    if tenant.preferred_city_id:
                        base_qs = CityModel.objects.filter(
                            pk=tenant.preferred_city_id
                        ).union(base_qs)
                except TenantDetailsModel.DoesNotExist:
                    pass

            kwargs["queryset"] = base_qs
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

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
class TenantPreferenceQuestionModelAdmin(TranslatableAdmin):
    list_display = ('id','title', 'question_type')
    search_fields = ('question_type',)
    readonly_fields = ('created_at', 'deleted_at')
    
@admin.register(TenantPreferenceOptionModel)
class TenantPreferenceOptionModelAdmin(TranslatableAdmin):
    list_display = ('id', 'title','question')
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
