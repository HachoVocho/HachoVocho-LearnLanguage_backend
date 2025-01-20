from django.urls import path
from .views import landlord_signup

urlpatterns = [
    path('signup/', landlord_signup, name='landlord-signup'),
]
