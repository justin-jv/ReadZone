import random

from django.conf import settings
from django.core.mail import send_mail


def generate_otp():
    return str(random.randint(100000, 999999))


def send_otp_email(email, otp):

    subject = "ReadZone Email Verification"

    message = f"""
Hello,

Your ReadZone verification code is:

{otp}

This OTP is valid for 60 seconds.

If you did not request this code, please ignore this email.

Regards,
ReadZone Team
"""

    send_mail(
        subject,
        message,
        settings.EMAIL_HOST_USER,
        [email],
        fail_silently=False,
    )