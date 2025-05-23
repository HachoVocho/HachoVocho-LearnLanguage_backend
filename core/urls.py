from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('api/cities/', views.city_autocomplete, name='city-autocomplete'),
    path('api/cities/<int:city_id>/properties/', views.properties_by_city, name='city-properties'),
]