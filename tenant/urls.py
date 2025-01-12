from django.urls import path
from .views import tenant_signup

urlpatterns = [
    path('signup/', tenant_signup, name='tenant-signup'),
]
