from django.urls import path
from .views import (
    forgot_password, 
    email_verification, 
    login, 
    update_password,
    send_otp,
    verify_otp
)

urlpatterns = [
    path('email_verification/', email_verification, name='email-verification'),
    path('login/', login, name='login'),
    path('forgot_password/', forgot_password, name='forgot_password'),
    path('update_password/', update_password, name='update_password'),
    path('send_otp_for_mobile/', send_otp, name='send-otp'),
    path('verify_otp_for_mobile/', verify_otp, name='verify-otp'),
]
