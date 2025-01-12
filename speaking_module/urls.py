from django.urls import path
from .views import GetFaceToFaceConversationsView

urlpatterns = [
    path('get_face_to_face_conversations/', GetFaceToFaceConversationsView.as_view(), name='get_face_to_face_conversations'),
]
