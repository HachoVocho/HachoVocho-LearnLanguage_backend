from django.urls import path
from .views import send_chat_message, get_chat_messages

urlpatterns = [
    path('send/', send_chat_message, name='send_chat_message'),
    path('get/', get_chat_messages, name='get_chat_messages'),
]
