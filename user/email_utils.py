from django.core.mail import send_mail
from django.forms import ValidationError

def send_otp_email(email, otp):
    """Helper function to send OTP email"""
    try:
        send_mail(
            subject='Verify Your Email',
            message=f'Your OTP for email verification is: {otp}',
            from_email=None,  # Uses DEFAULT_FROM_EMAIL in settings.py
            recipient_list=[email],
            fail_silently=False,  # Raise error if email fails
        )
    except Exception as e:
        raise ValidationError(f"Failed to send email: {str(e)}")