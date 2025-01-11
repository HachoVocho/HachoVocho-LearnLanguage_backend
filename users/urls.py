# users/urls.py

from django.urls import path
from .views import FetchTopicsProgressView, MarkSentenceListenedView, MarkStoryListenedView, UserSignupView, OTPVerificationView, UserLoginView

urlpatterns = [
    path('signup/', UserSignupView.as_view(), name='signup'),
    path('verify-email/', OTPVerificationView.as_view(), name='verify-otp'),
    path('login/', UserLoginView.as_view(), name='login'),  # ← Add this
    path('topics-progress/', FetchTopicsProgressView.as_view(), name='topics_progress'),
    path('mark-sentence-listened/', MarkSentenceListenedView.as_view(), name='mark_sentence_listened'),
    path('mark-story-listened/', MarkStoryListenedView.as_view(), name='mark_story_listened'),
]
