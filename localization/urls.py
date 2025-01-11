from django.urls import path
from .views import StaticStringsAPIView

urlpatterns = [
    path('get-static-strings/', StaticStringsAPIView.as_view(), name='static_strings_api'),
]