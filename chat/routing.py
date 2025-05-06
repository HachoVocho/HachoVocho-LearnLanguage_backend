# chat/routing.py
from django.urls import re_path
from .consumers import TenantChatConsumer, LandlordChatConsumer

websocket_urlpatterns = [
    # Tenant‐side connections
    re_path(r'ws/chat/tenant/$', TenantChatConsumer.as_asgi()),
    # Landlord‐side connections
    re_path(r'ws/chat/landlord/$', LandlordChatConsumer.as_asgi()),
]
