# dashboard/routing.py
from django.urls import re_path
from .consumers import TenantDashboardConsumer

websocket_urlpatterns = [
    re_path(r'ws/tenant_dashboard/$', TenantDashboardConsumer.as_asgi()),
]
