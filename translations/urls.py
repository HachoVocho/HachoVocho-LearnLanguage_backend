from django.urls import path
from .views import add_translation, get_translations, add_language, get_languages

urlpatterns = [
    path('add_translation/', add_translation, name='add-translation'),
    path('get_translations/', get_translations, name='get-translations'),
    path('add_language/', add_language, name='add-language'),
    path('get_languages/', get_languages, name='get-languages'),
]
