# chat/routing.py
from django.urls import re_path
from .consumers import LandlordInterestRequestConsumer, TenantInterestRequestConsumer

websocket_urlpatterns = [
    re_path('ws/tenant_interest_request/', TenantInterestRequestConsumer.as_asgi()),
    re_path('ws/landlord_interest_request/', LandlordInterestRequestConsumer.as_asgi()),
]
