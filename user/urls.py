from django.urls import path
from .views import get_user_roles
from .views import email_verification

urlpatterns = [
    path('get_roles/', get_user_roles, name='get-user-roles'),
    path('email_verification/', email_verification, name='email-verification'),
]
