from django.urls import path
from .views import forgot_password, get_user_roles, email_verification, login, update_password

urlpatterns = [
    path('get_roles/', get_user_roles, name='get-user-roles'),
    path('email_verification/', email_verification, name='email-verification'),
    path('login/', login, name='login'),  # Added the login path
    path('forgot_password/', forgot_password, name='forgot_password'),  # Added the login path
    path('update_password/', update_password, name='update_password'),  # Added the login path
]
