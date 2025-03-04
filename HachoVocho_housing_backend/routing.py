# your_project/routing.py
from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter
import chat.routing as chatRouting
import interest_requests.routing as landlordRouting
import landlord_availability.routing as landlordAvailabilityRouting

application = ProtocolTypeRouter({
  "websocket": AuthMiddlewareStack(
    URLRouter(
      chatRouting.websocket_urlpatterns + 
      landlordRouting.websocket_urlpatterns + 
      landlordAvailabilityRouting.websocket_urlpatterns
    )
  ),
})
