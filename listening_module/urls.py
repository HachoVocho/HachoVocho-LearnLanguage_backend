# users/urls.py

from django.urls import path

from listening_module.views import GetListeningDataByTopicView

urlpatterns = [
    path('get_sentences_by_topic/', GetListeningDataByTopicView.as_view(), name='get_sentences_by_topic'),
]
