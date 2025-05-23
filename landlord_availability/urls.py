from django.urls import path
from .views import add_landlord_availability, delete_landlord_availability_slot, get_landlord_availability_slots, get_landlord_availability_dates

urlpatterns = [
    path("add_landlord_availability/", add_landlord_availability, name="add_landlord_availability"),
    path("get_landlord_availability_slots/", get_landlord_availability_slots, name="get_landlord_availability_slots"),
    path("get_landlord_availability_dates/", get_landlord_availability_dates, name="get_landlord_availability_dates"),
    path('delete_availability_slot/', delete_landlord_availability_slot, name='delete_slot'),
]
