"""
Models for the accounts app.

Indexes optimized for OTP lookups and profile queries.
"""

from django.conf import settings
from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator
from django.utils import timezone


class UserProfile(models.Model):
    """Extended user profile with Firebase integration."""

    AUTH_PROVIDERS = [
        ('email', 'Email'),
        ('google', 'Google'),
        ('github', 'GitHub'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    firebase_uid = models.CharField(max_length=128, unique=True, null=True, blank=True)
    auth_provider = models.CharField(max_length=20, choices=AUTH_PROVIDERS, default='email')
    avatar = models.ImageField(upload_to='avatars/', blank=True)
    bio = models.TextField(max_length=500, blank=True)
    location = models.CharField(max_length=100, blank=True)
    total_carbon_saved = models.DecimalField(
        max_digits=10, decimal_places=2, default=0.00,
        validators=[MinValueValidator(0)],
    )
    is_email_verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username}'s Profile"

    class Meta:
        ordering = ['-created_at']


class EmailOTP(models.Model):
    """
    Stores hashed OTP codes for email verification.

    OTP codes are hashed before storage for security.
    Use django.contrib.auth.hashers.check_password() to verify.
    """

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='otps')
    otp_code = models.CharField(max_length=128)  # Stores hashed OTP
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False, db_index=True)
    attempts = models.IntegerField(default=0)

    def is_valid(self):
        """Check if this OTP is still valid (not used, not expired, under max attempts)."""
        max_attempts = getattr(settings, 'OTP_MAX_ATTEMPTS', 5)
        return (
            not self.is_used
            and self.expires_at > timezone.now()
            and self.attempts < max_attempts
        )

    def __str__(self):
        return f"OTP for {self.user.username} - {'Valid' if self.is_valid() else 'Expired'}"

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'is_used', '-created_at']),
        ]
