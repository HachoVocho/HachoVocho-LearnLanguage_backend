from django.urls import path
from .views import get_appointments

urlpatterns = [
    path('get_appointments/', get_appointments, name='get_appointments'),
]