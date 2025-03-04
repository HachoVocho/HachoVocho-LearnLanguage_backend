from django.urls import path
from .views import get_cities

urlpatterns = [
    path('get_cities/', get_cities, name='get_cities'),
]
