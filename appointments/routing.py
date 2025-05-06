from django.urls import re_path
from .consumers import TenantAppointmentConsumer, LandlordAppointmentConsumer

websocket_urlpatterns = [
    re_path(r'ws/tenant_appointments/$', TenantAppointmentConsumer.as_asgi()),
    re_path(r'ws/landlord_appointments/$', LandlordAppointmentConsumer.as_asgi()),
]
