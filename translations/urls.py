from django.urls import path
from .views import (
    add_translation, get_translations,
    add_language, get_languages, set_landlord_language,
    set_tenant_language,
)

urlpatterns = [
    path('add_translation/', add_translation, name='add-translation'),
    path('get_translations/', get_translations, name='get-translations'),
    path('add_language/', add_language, name='add-language'),
    path('get_languages/', get_languages, name='get-languages'),
    path('set_tenant_language/', set_tenant_language, name='set-tenant-language'),
    path('set_landlord_language/', set_landlord_language, name='set-landlord-language'),
]
