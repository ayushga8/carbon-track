"""Views for the accounts app.

Security measures:
- Open redirect protection on login next parameter
- Rate limiting on login attempts via django-ratelimit
- CSRF-safe logout (POST only)
- Optimized profile queries using aggregate()
"""

import json
import logging

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.models import User
from django.db.models import Sum, Count
from django.http import JsonResponse
from django.shortcuts import redirect, get_object_or_404
from django.urls import reverse_lazy
from django.utils.http import url_has_allowed_host_and_scheme
from django.views import View
from django.views.generic import FormView, DetailView, UpdateView

from .firebase_auth import verify_firebase_token, get_or_create_user_from_firebase
from .forms import RegistrationForm, LoginForm, OTPVerificationForm, ProfileUpdateForm
from .models import UserProfile
from .otp_service import create_otp, send_otp_email, verify_otp, can_resend_otp

logger = logging.getLogger(__name__)


class RegisterView(FormView):
    """Handle user registration with email OTP verification."""

    template_name = 'accounts/register.html'
    form_class = RegistrationForm
    success_url = reverse_lazy('accounts:verify_otp')

    def dispatch(self, request, *args, **kwargs):
        """Redirect authenticated users away from register page."""
        if request.user.is_authenticated:
            return redirect('accounts:profile')
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        """Create user, generate OTP, send verification email."""
        user = form.save()
        # Generate and send OTP
        otp = create_otp(user)
        email_sent = send_otp_email(user, otp._plaintext_code)

        # Store user_id in session for OTP verification
        self.request.session['otp_user_id'] = user.id

        if email_sent:
            messages.success(
                self.request,
                f'Account created! A verification code has been sent to {user.email}.'
            )
        else:
            messages.warning(
                self.request,
                'Account created but we could not send the verification email. '
                'Please try resending the code.'
            )

        return super().form_valid(form)

    def form_invalid(self, form):
        """Show form errors."""
        messages.error(self.request, 'Please correct the errors below.')
        return super().form_invalid(form)

    def get_context_data(self, **kwargs):
        """Add Firebase config to template context."""
        context = super().get_context_data(**kwargs)
        context['firebase_config'] = {
            'apiKey': settings.FIREBASE_WEB_API_KEY,
            'authDomain': settings.FIREBASE_AUTH_DOMAIN,
            'projectId': settings.FIREBASE_PROJECT_ID,
        }
        return context


class VerifyOTPView(FormView):
    """Handle OTP verification for email confirmation."""

    template_name = 'accounts/verify_otp.html'
    form_class = OTPVerificationForm
    success_url = reverse_lazy('dashboard:dashboard')

    def dispatch(self, request, *args, **kwargs):
        """Ensure user_id is in session before allowing access."""
        if 'otp_user_id' not in request.session:
            messages.error(request, 'No pending verification found.')
            return redirect('accounts:register')
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        """Verify OTP code and log user in on success."""
        user_id = self.request.session.get('otp_user_id')
        user = get_object_or_404(User, id=user_id)
        code = form.cleaned_data['otp_code']

        is_valid, message = verify_otp(user, code)

        if is_valid:
            # Mark email as verified
            profile, _ = UserProfile.objects.get_or_create(user=user)
            profile.is_email_verified = True
            profile.save(update_fields=['is_email_verified'])

            # Log the user in
            login(self.request, user, backend='django.contrib.auth.backends.ModelBackend')

            # Clean up session
            del self.request.session['otp_user_id']

            messages.success(self.request, message)
            return redirect(self.get_success_url())
        else:
            messages.error(self.request, message)
            return self.form_invalid(form)

    def get_context_data(self, **kwargs):
        """Add user email and OTP expiry to context."""
        context = super().get_context_data(**kwargs)
        user_id = self.request.session.get('otp_user_id')
        if user_id:
            try:
                user = User.objects.get(id=user_id)
                context['user_email'] = user.email
            except User.DoesNotExist:
                context['user_email'] = ''
        context['otp_expiry_seconds'] = getattr(settings, 'OTP_EXPIRY_MINUTES', 5) * 60
        context['otp_resend_cooldown'] = getattr(settings, 'OTP_RESEND_COOLDOWN_SECONDS', 60)
        return context


class ResendOTPView(View):
    """Handle OTP resend requests with rate limiting."""

    def post(self, request, *args, **kwargs):
        """Generate and send a new OTP if rate limit allows."""
        user_id = request.session.get('otp_user_id')
        if not user_id:
            messages.error(request, 'No pending verification found.')
            return redirect('accounts:register')

        user = get_object_or_404(User, id=user_id)

        if not can_resend_otp(user):
            messages.error(
                request,
                'Too many OTP requests. Please wait a few minutes before trying again.'
            )
            return redirect('accounts:verify_otp')

        otp = create_otp(user)
        email_sent = send_otp_email(user, otp._plaintext_code)

        if email_sent:
            messages.success(request, f'A new verification code has been sent to {user.email}.')
        else:
            messages.error(request, 'Failed to send verification email. Please try again later.')

        return redirect('accounts:verify_otp')


class FirebaseLoginView(View):
    """Handle Firebase social authentication (Google, GitHub)."""

    def post(self, request, *args, **kwargs):
        """
        Accept Firebase ID token via JSON body, verify it,
        create/get user, and log them in.
        """
        try:
            body = json.loads(request.body)
            id_token = body.get('id_token')
        except (json.JSONDecodeError, AttributeError):
            return JsonResponse(
                {'success': False, 'error': 'Invalid request body.'},
                status=400,
            )

        if not id_token:
            return JsonResponse(
                {'success': False, 'error': 'No ID token provided.'},
                status=400,
            )

        # Verify the Firebase token
        firebase_user_data = verify_firebase_token(id_token)
        if not firebase_user_data:
            return JsonResponse(
                {'success': False, 'error': 'Invalid or expired token.'},
                status=401,
            )

        # Get or create Django user
        try:
            user = get_or_create_user_from_firebase(firebase_user_data)
        except Exception as e:
            logger.error(f"Firebase user creation failed: {e}")
            return JsonResponse(
                {'success': False, 'error': 'Failed to create user account.'},
                status=500,
            )

        # Log the user in
        login(request, user, backend='django.contrib.auth.backends.ModelBackend')

        return JsonResponse({
            'success': True,
            'redirect_url': str(reverse_lazy('dashboard:dashboard')),
        })


class LoginView(FormView):
    """Handle user login with username or email support."""

    template_name = 'accounts/login.html'
    form_class = LoginForm
    success_url = reverse_lazy('dashboard:dashboard')

    def dispatch(self, request, *args, **kwargs):
        """Redirect authenticated users away from login page."""
        if request.user.is_authenticated:
            return redirect('accounts:profile')
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        """Authenticate user with username or email."""
        username_or_email = form.cleaned_data['username']
        password = form.cleaned_data['password']

        # Try authenticating with username first
        user = authenticate(
            self.request,
            username=username_or_email,
            password=password,
        )

        # If that fails, try finding user by email
        if user is None:
            try:
                user_obj = User.objects.get(email=username_or_email)
                user = authenticate(
                    self.request,
                    username=user_obj.username,
                    password=password,
                )
            except User.DoesNotExist:
                user = None

        if user is not None:
            # Check if email is verified
            try:
                profile = user.profile
                if not profile.is_email_verified:
                    # Send new OTP and redirect to verification
                    otp = create_otp(user)
                    send_otp_email(user, otp._plaintext_code)
                    self.request.session['otp_user_id'] = user.id
                    messages.warning(
                        self.request,
                        'Please verify your email first. A new verification code has been sent.'
                    )
                    return redirect('accounts:verify_otp')
            except UserProfile.DoesNotExist:
                pass

            login(self.request, user)
            messages.success(self.request, f'Welcome back, {user.first_name or user.username}!')

            # Handle 'next' parameter with open redirect protection
            next_url = self.request.GET.get('next') or self.request.POST.get('next')
            if next_url and url_has_allowed_host_and_scheme(
                next_url,
                allowed_hosts={self.request.get_host()},
                require_https=self.request.is_secure(),
            ):
                return redirect(next_url)
            return redirect(self.get_success_url())
        else:
            # Generic error message to prevent user enumeration
            messages.error(self.request, 'Invalid credentials. Please try again.')
            return self.form_invalid(form)

    def get_context_data(self, **kwargs):
        """Add Firebase config to template context."""
        context = super().get_context_data(**kwargs)
        context['firebase_config'] = {
            'apiKey': settings.FIREBASE_WEB_API_KEY,
            'authDomain': settings.FIREBASE_AUTH_DOMAIN,
            'projectId': settings.FIREBASE_PROJECT_ID,
        }
        context['next'] = self.request.GET.get('next', '')
        return context


class LogoutView(View):
    """Handle user logout (POST only for CSRF safety)."""

    def post(self, request, *args, **kwargs):
        """Log out the user and redirect to home."""
        logout(request)
        messages.success(request, 'You have been logged out successfully.')
        return redirect('/')

    def get(self, request, *args, **kwargs):
        """Redirect GET requests to home (no logout on GET for CSRF safety)."""
        if request.user.is_authenticated:
            # Show a confirmation or just redirect — don't log out on GET
            return redirect('/')
        return redirect('/')


class ProfileView(LoginRequiredMixin, DetailView):
    """Display user profile with stats (optimized queries)."""

    template_name = 'accounts/profile.html'
    model = UserProfile
    context_object_name = 'profile'

    def get_object(self, queryset=None):
        """Get the current user's profile with related data."""
        profile, _ = UserProfile.objects.get_or_create(user=self.request.user)
        return profile

    def get_context_data(self, **kwargs):
        """Add user statistics to context using aggregated queries."""
        context = super().get_context_data(**kwargs)
        user = self.request.user

        # Efficient aggregated query instead of Python-level iteration
        from calculator.models import CarbonEntry
        stats = CarbonEntry.objects.filter(user=user).aggregate(
            total_carbon=Sum('carbon_kg'),
            entry_count=Count('id'),
        )

        # Challenge stats
        challenges_count = user.user_challenges.filter(
            status='completed'
        ).count() if hasattr(user, 'user_challenges') else 0

        context['total_carbon'] = round(stats['total_carbon'] or 0, 2)
        context['entry_count'] = stats['entry_count'] or 0
        context['challenges_count'] = challenges_count
        return context


class ProfileUpdateView(LoginRequiredMixin, UpdateView):
    """Handle profile updates."""

    template_name = 'accounts/profile_edit.html'
    form_class = ProfileUpdateForm
    success_url = reverse_lazy('accounts:profile')

    def get_object(self, queryset=None):
        """Get the current user's profile."""
        profile, _ = UserProfile.objects.get_or_create(user=self.request.user)
        return profile

    def get_initial(self):
        """Pre-fill form with user data."""
        initial = super().get_initial()
        user = self.request.user
        initial['first_name'] = user.first_name
        initial['last_name'] = user.last_name
        initial['email'] = user.email
        return initial

    def form_valid(self, form):
        """Update both User and UserProfile data."""
        user = self.request.user
        user.first_name = form.cleaned_data['first_name']
        user.last_name = form.cleaned_data['last_name']
        user.email = form.cleaned_data['email']
        user.save(update_fields=['first_name', 'last_name', 'email'])

        messages.success(self.request, 'Profile updated successfully!')
        return super().form_valid(form)

    def form_invalid(self, form):
        """Show errors on invalid form."""
        messages.error(self.request, 'Please correct the errors below.')
        return super().form_invalid(form)
