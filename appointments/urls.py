from django.urls import path
from .views import (
    book_appointment,
    get_tenant_appointments,
    get_landlord_appointments,
)

urlpatterns = [
    path('get_tenant_appointments/', get_tenant_appointments, name='get_tenant_appointments'),
    path('get_landlord_appointments/', get_landlord_appointments, name='get_landlord_appointments'),
    path('book_appointment/',            # ← new
         book_appointment,
         name='book_appointment'),
]
