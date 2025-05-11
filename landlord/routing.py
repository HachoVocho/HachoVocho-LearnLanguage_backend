# dashboard/routing.py
from django.urls import re_path
from .consumers import LandlordDashboardConsumer

websocket_urlpatterns = [
    re_path(r'ws/landlord_dashboard/$', LandlordDashboardConsumer.as_asgi()),
]
