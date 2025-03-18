from django.urls import path
from .views import (
    add_identity_document, add_landlord_property_details, delete_identity_document, get_all_identity_documents, get_profile_details, get_preference_questions,
    get_property_types_and_amenities, landlord_signup,
    save_landlord_preferences, get_landlord_properties,
    get_landlord_property_details, toggle_active_status, update_identity_document, update_landlord_property_details, update_profile_details, update_uploaded_landlord_media_selection, upload_landlord_media_selection,
)

urlpatterns = [
    path('signup/', landlord_signup, name='landlord_signup'),
    path('get_preference_questions/', get_preference_questions, name='get_preference_questions'),
    path('save_preferences/', save_landlord_preferences, name='save_landlord_preferences'),
    path('add_landlord_property_details/', add_landlord_property_details, name='add_landlord_property_details'),
    path('update_landlord_property_details/', update_landlord_property_details, name='update_landlord_property_details'),
    path('get_property_types_and_amenities/', get_property_types_and_amenities, name='get_property_type_and_amenities'),
    path('get_landlord_properties/', get_landlord_properties, name='get_landlord_properties'),
    path('get_landlord_property_details/', get_landlord_property_details, name='get_landlord_property_details'),
    path('get_profile_details/', get_profile_details, name='get_profile_details'),
    path('update_profile_details/', update_profile_details, name='update_profile_details'),
    path('add_identity_document/', add_identity_document, name='add_identity_document'),
    path('get_all_identity_documents/', get_all_identity_documents, name='get_all_identity_documents'),
    path('update_identity_document/', update_identity_document, name='update_identity_document'),
    path('delete_identity_document/', delete_identity_document, name='delete_identity_document'),
    path('upload_landlord_media_selection/', upload_landlord_media_selection, name='upload_landlord_media_selection'),
    path('update_uploaded_landlord_media_selection/', update_uploaded_landlord_media_selection, name='update_uploaded_landlord_media_selection'),
    path('toggle_active_status/', toggle_active_status, name='toggle_active_status'),
]