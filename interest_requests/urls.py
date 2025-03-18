# your_app/urls.py

from django.urls import path
from .views import get_active_tenants_view

urlpatterns = [
    path('get-active-tenants/', get_active_tenants_view, name='get_active_tenants'),
]
