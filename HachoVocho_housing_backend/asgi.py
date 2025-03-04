# asgi.py (corrected version)
import os

# Set environment variable FIRST
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "HachoVocho_housing_backend.settings")

# Now import Django components
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack

# Initialize Django ASGI application early
django_asgi_app = get_asgi_application()

# Import routing components AFTER Django setup
import chat.routing
import interest_requests.routing
import landlord_availability.routing

application = ProtocolTypeRouter({
    "http": django_asgi_app,
    "websocket": AuthMiddlewareStack(
        URLRouter(
            chat.routing.websocket_urlpatterns + interest_requests.routing.websocket_urlpatterns
            + landlord_availability.routing.websocket_urlpatterns
        )
    ),
})