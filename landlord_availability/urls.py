from django.urls import path
from .views import add_landlord_availability, get_landlord_availability_by_month, get_landlord_availability_by_property

urlpatterns = [
    path("add_availability/", add_landlord_availability, name="add_landlord_availability"),
    path("get_landlord_availability_by_month/", get_landlord_availability_by_month, name="get_landlord_availability_by_month"),
    path("get_landlord_availability_by_property/", get_landlord_availability_by_property, name="get_landlord_availability_by_property"),
]
