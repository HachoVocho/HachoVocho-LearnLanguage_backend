from django.urls import path
from .views import get_cities, get_countries

urlpatterns = [
    path('get_cities/', get_cities, name='get_cities'),
    path('get_countries/', get_countries, name='get_countries'),
]
