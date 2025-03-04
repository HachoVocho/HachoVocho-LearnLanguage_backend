from django.urls import path
from .views import (
    get_properties_by_city_overview,
    get_property_details,
    get_tenant_profile_details, 
    tenant_signup, 
    save_tenant_preferences, 
    get_tenant_preference_questions_answers,
    add_identity_document,
    get_all_identity_documents,
    update_identity_document,
    delete_identity_document,
    update_tenant_personality,
    update_tenant_profile_details
)

urlpatterns = [
    path('signup/', tenant_signup, name='tenant_signup'),
    path('get_tenant_preference_questions/', get_tenant_preference_questions_answers, name='get_tenant_preference_questions_answers'),
    path('save_tenant_preferences/', save_tenant_preferences, name='save_tenant_preferences'),
    path('get_tenant_profile_details/', get_tenant_profile_details, name='get_tenant_profile_details'),
    path('update_tenant_profile_details/', update_tenant_profile_details, name='update_tenant_profile_details'),
    path('update_tenant_personality/', update_tenant_personality, name='update_tenant_personality'),
    path('add_identity_document/', add_identity_document, name='add_identity_document'),
    path('get_all_identity_documents/', get_all_identity_documents, name='get_all_identity_documents'),
    path('update_identity_document/', update_identity_document, name='update_identity_document'),
    path('delete_identity_document/', delete_identity_document, name='delete_identity_document'),
    path('get_properties_by_city_overview/', get_properties_by_city_overview, name='get_properties_by_city_overview'),
    path('get_property_details/', get_property_details, name='get_property_details'),
]
