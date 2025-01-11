from django.urls import re_path
from .consumers import BotConversationConsumer

websocket_urlpatterns = [
    re_path(r'ws/bot_conversation/$', BotConversationConsumer.as_asgi()),
]
