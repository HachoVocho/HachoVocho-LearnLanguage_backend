import os
from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter
from django.core.asgi import get_asgi_application
import audio_processing.routing
import chatbot.routing

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'HachoVocho_learn_language_backend.settings')

application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    "websocket": AuthMiddlewareStack(
        URLRouter(
            audio_processing.routing.websocket_urlpatterns +
            chatbot.routing.websocket_urlpatterns
        )
    ),
})
