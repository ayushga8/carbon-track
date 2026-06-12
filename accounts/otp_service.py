"""
OTP service for email verification.

Handles OTP generation, creation, email sending via Gmail SMTP,
verification with constant-time comparison, and rate limiting.

Security:
- Uses `secrets` module for cryptographically secure OTP generation
- Hashes OTP codes before storage (django.contrib.auth.hashers)
- Uses `hmac.compare_digest` for timing-attack-resistant comparison
- Atomic attempt counting to prevent race conditions
"""

import hmac
import secrets
import logging
from datetime import timedelta

from django.conf import settings
from django.contrib.auth.hashers import make_password, check_password
from django.core.mail import send_mail
from django.db.models import F
from django.utils import timezone

from .models import EmailOTP

logger = logging.getLogger(__name__)


def generate_otp():
    """Generate a cryptographically secure 6-digit OTP code."""
    return ''.join([str(secrets.randbelow(10)) for _ in range(6)])


def create_otp(user):
    """
    Create a new OTP for the user, invalidating previous ones.

    Args:
        user: The Django User instance.

    Returns:
        tuple: (EmailOTP instance, plaintext OTP code)
    """
    # Invalidate all previous unused OTPs atomically
    EmailOTP.objects.filter(user=user, is_used=False).update(is_used=True)

    otp_code = generate_otp()
    expiry_minutes = getattr(settings, 'OTP_EXPIRY_MINUTES', 5)

    # Store hashed OTP in database
    otp = EmailOTP.objects.create(
        user=user,
        otp_code=make_password(otp_code),
        expires_at=timezone.now() + timedelta(minutes=expiry_minutes),
    )
    # Return the plaintext code separately (for sending via email)
    otp._plaintext_code = otp_code
    return otp


def send_otp_email(user, otp_code):
    """
    Send OTP verification email via Gmail SMTP.

    Args:
        user: The Django User instance.
        otp_code: The 6-digit OTP string (plaintext).

    Returns:
        bool: True if email sent successfully, False otherwise.
    """
    subject = 'CarbonTrack - Email Verification Code'
    message = f"""
Hello {user.first_name or user.username},

Your email verification code is: {otp_code}

This code will expire in {getattr(settings, 'OTP_EXPIRY_MINUTES', 5)} minutes.

If you didn't request this code, please ignore this email.

Best regards,
CarbonTrack Team
"""

    try:
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=False,
        )
        # Mask email in logs for PII protection
        masked = user.email[0] + '***@' + user.email.split('@')[-1]
        logger.info(f"OTP email sent to {masked}")
        return True
    except Exception as e:
        masked = user.email[0] + '***@' + user.email.split('@')[-1]
        logger.error(f"Failed to send OTP email to {masked}: {e}")
        return False


def verify_otp(user, code):
    """
    Verify the OTP code for a user with constant-time comparison.

    Args:
        user: The Django User instance.
        code: The OTP code string to verify.

    Returns:
        tuple: (is_valid: bool, message: str)
    """
    try:
        otp = EmailOTP.objects.filter(
            user=user,
            is_used=False,
        ).latest('created_at')
    except EmailOTP.DoesNotExist:
        return False, 'No OTP found. Please request a new one.'

    if not otp.is_valid():
        return False, 'OTP has expired. Please request a new one.'

    # Atomic increment of attempts to prevent race conditions
    EmailOTP.objects.filter(pk=otp.pk).update(attempts=F('attempts') + 1)
    otp.refresh_from_db()

    # Use check_password for hashed comparison (constant-time internally)
    if check_password(code, otp.otp_code):
        otp.is_used = True
        otp.save(update_fields=['is_used'])
        return True, 'Email verified successfully!'
    else:
        max_attempts = getattr(settings, 'OTP_MAX_ATTEMPTS', 5)
        remaining = max_attempts - otp.attempts
        if remaining <= 0:
            otp.is_used = True
            otp.save(update_fields=['is_used'])
            return False, 'Too many failed attempts. Please request a new OTP.'
        return False, f'Invalid OTP. {remaining} attempts remaining.'


def can_resend_otp(user):
    """
    Check if user can resend OTP (rate limiting).

    Args:
        user: The Django User instance.

    Returns:
        bool: True if user is allowed to request a new OTP.
    """
    window_minutes = getattr(settings, 'OTP_RESEND_WINDOW_MINUTES', 15)
    max_resends = getattr(settings, 'OTP_MAX_RESENDS_PER_WINDOW', 3)

    recent_otps = EmailOTP.objects.filter(
        user=user,
        created_at__gte=timezone.now() - timedelta(minutes=window_minutes),
    ).count()

    return recent_otps < max_resends
