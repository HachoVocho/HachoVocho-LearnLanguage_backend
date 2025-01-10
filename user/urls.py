from django.urls import path
from .views import get_user_roles

urlpatterns = [
    path('get_roles/', get_user_roles, name='get-user-roles'),
]
