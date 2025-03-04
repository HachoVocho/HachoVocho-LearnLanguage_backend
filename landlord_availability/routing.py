# landlord_availability/routing.py

from django.urls import re_path
from .consumers import LandlordAvailabilityConsumer

websocket_urlpatterns = [
    re_path('ws/landlord_availability/', LandlordAvailabilityConsumer.as_asgi()),
]
