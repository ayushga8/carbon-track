"""
Forms for the accounts app.

Security:
- Username regex validation to prevent XSS/injection
- Server-side avatar file validation (type, size)
- Email uniqueness check on profile update
- Password validation with user context for similarity checks
"""

import re

from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError

from .models import UserProfile

# Max avatar file size: 5 MB
MAX_AVATAR_SIZE = 5 * 1024 * 1024
ALLOWED_IMAGE_TYPES = ['image/jpeg', 'image/png', 'image/gif', 'image/webp']


class RegistrationForm(forms.ModelForm):
    """User registration form with strong password validation."""

    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'class': 'form-input',
            'placeholder': 'Enter your email',
            'aria-label': 'Email address',
            'autocomplete': 'email',
            'id': 'register-email',
        })
    )
    username = forms.CharField(
        max_length=30,
        min_length=3,
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': 'Choose a username',
            'aria-label': 'Username',
            'autocomplete': 'username',
            'id': 'register-username',
        })
    )
    first_name = forms.CharField(
        max_length=30,
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': 'First name',
            'aria-label': 'First name',
            'id': 'register-first-name',
        })
    )
    last_name = forms.CharField(
        max_length=30,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': 'Last name',
            'aria-label': 'Last name',
            'id': 'register-last-name',
        })
    )
    password1 = forms.CharField(
        label='Password',
        widget=forms.PasswordInput(attrs={
            'class': 'form-input',
            'placeholder': 'Create a password',
            'aria-label': 'Password',
            'autocomplete': 'new-password',
            'id': 'register-password1',
        })
    )
    password2 = forms.CharField(
        label='Confirm Password',
        widget=forms.PasswordInput(attrs={
            'class': 'form-input',
            'placeholder': 'Confirm your password',
            'aria-label': 'Confirm password',
            'autocomplete': 'new-password',
            'id': 'register-password2',
        })
    )

    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name']

    def clean_username(self):
        """Validate username format: alphanumeric + underscores only."""
        username = self.cleaned_data.get('username')
        if not re.match(r'^[a-zA-Z0-9_]+$', username):
            raise forms.ValidationError(
                'Username can only contain letters, numbers, and underscores.'
            )
        return username

    def clean_email(self):
        """Ensure email is unique across all users."""
        email = self.cleaned_data.get('email').lower()
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError('An account with this email already exists.')
        return email

    def clean_password1(self):
        """Validate password strength with user context."""
        password = self.cleaned_data.get('password1')
        # Build a temporary user to check password similarity against username/email
        temp_user = User(
            username=self.cleaned_data.get('username', ''),
            email=self.cleaned_data.get('email', ''),
        )
        validate_password(password, user=temp_user)
        return password

    def clean(self):
        """Ensure both passwords match."""
        cleaned_data = super().clean()
        password1 = cleaned_data.get('password1')
        password2 = cleaned_data.get('password2')
        if password1 and password2 and password1 != password2:
            self.add_error('password2', 'Passwords do not match.')
        return cleaned_data

    def save(self, commit=True):
        """Create user with hashed password and associated profile."""
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password1'])
        user.email = user.email.lower()
        if commit:
            user.save()
            UserProfile.objects.get_or_create(
                user=user, defaults={'auth_provider': 'email'}
            )
        return user


class LoginForm(forms.Form):
    """Login form with email/username support."""

    username = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': 'Username or email',
            'aria-label': 'Username or email',
            'autocomplete': 'username',
            'id': 'login-username',
        })
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-input',
            'placeholder': 'Enter your password',
            'aria-label': 'Password',
            'autocomplete': 'current-password',
            'id': 'login-password',
        })
    )


class OTPVerificationForm(forms.Form):
    """OTP verification form with 6-digit input."""

    otp_code = forms.CharField(
        max_length=6,
        min_length=6,
        widget=forms.TextInput(attrs={
            'class': 'form-input otp-input',
            'placeholder': '000000',
            'aria-label': 'Enter 6-digit verification code',
            'autocomplete': 'one-time-code',
            'inputmode': 'numeric',
            'pattern': '[0-9]{6}',
            'maxlength': '6',
            'autofocus': True,
            'id': 'otp-code-input',
        })
    )

    def clean_otp_code(self):
        """Ensure OTP contains only digits."""
        code = self.cleaned_data.get('otp_code')
        if not code.isdigit():
            raise forms.ValidationError('OTP must contain only digits.')
        return code


class ProfileUpdateForm(forms.ModelForm):
    """User profile update form with server-side validation."""

    first_name = forms.CharField(
        max_length=30,
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'aria-label': 'First name',
            'id': 'profile-first-name',
        })
    )
    last_name = forms.CharField(
        max_length=30,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'aria-label': 'Last name',
            'id': 'profile-last-name',
        })
    )
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'class': 'form-input',
            'aria-label': 'Email address',
            'id': 'profile-email',
        })
    )

    class Meta:
        model = UserProfile
        fields = ['bio', 'location', 'avatar']
        widgets = {
            'bio': forms.Textarea(attrs={
                'class': 'form-input',
                'rows': 4,
                'maxlength': '500',
                'placeholder': 'Tell us about yourself...',
                'aria-label': 'Bio',
                'id': 'profile-bio',
            }),
            'location': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Your city or country',
                'aria-label': 'Location',
                'id': 'profile-location',
            }),
            'avatar': forms.FileInput(attrs={
                'class': 'form-input',
                'aria-label': 'Profile picture',
                'accept': 'image/jpeg,image/png,image/gif,image/webp',
                'id': 'profile-avatar',
            }),
        }

    def clean_email(self):
        """Ensure email is unique (excluding current user)."""
        email = self.cleaned_data.get('email').lower()
        current_user = self.instance.user if self.instance and self.instance.pk else None
        qs = User.objects.filter(email=email)
        if current_user:
            qs = qs.exclude(pk=current_user.pk)
        if qs.exists():
            raise forms.ValidationError('This email is already in use by another account.')
        return email

    def clean_avatar(self):
        """Validate avatar file type and size."""
        avatar = self.cleaned_data.get('avatar')
        if avatar and hasattr(avatar, 'content_type'):
            # Check file type
            if avatar.content_type not in ALLOWED_IMAGE_TYPES:
                raise forms.ValidationError(
                    'Only JPEG, PNG, GIF, and WebP images are allowed.'
                )
            # Check file size
            if avatar.size > MAX_AVATAR_SIZE:
                raise forms.ValidationError(
                    f'Image file size must be under {MAX_AVATAR_SIZE // (1024*1024)}MB.'
                )
        return avatar
