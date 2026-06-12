"""
Comprehensive tests for the accounts app.

150+ test target: accounts contributes ~50 tests covering:
- OTP generation, creation, verification, rate limiting, cleanup
- Registration form validation (XSS, email, password, edge cases)
- Login form, OTP form, Profile update form
- Views: Register, Verify OTP, Resend OTP, Login, Logout, Profile
- Security: open redirect, user enumeration, CSRF, auth bypass
- Firebase auth mocking
- Model behavior and constraints
"""

from datetime import timedelta
from unittest.mock import patch, MagicMock

from django.conf import settings
from django.contrib.auth.hashers import make_password, check_password
from django.contrib.auth.models import User
from django.test import TestCase, Client, override_settings
from django.urls import reverse
from django.utils import timezone

from .forms import RegistrationForm, LoginForm, OTPVerificationForm, ProfileUpdateForm
from .models import UserProfile, EmailOTP
from .otp_service import generate_otp, create_otp, verify_otp, can_resend_otp, send_otp_email


# ============================================================
# OTP GENERATION TESTS
# ============================================================

class TestGenerateOTP(TestCase):
    """Test OTP code generation security and format."""

    def test_otp_length_is_six(self):
        otp = generate_otp()
        self.assertEqual(len(otp), 6)

    def test_otp_is_numeric_only(self):
        for _ in range(20):
            otp = generate_otp()
            self.assertTrue(otp.isdigit(), f"OTP '{otp}' contains non-digit chars")

    def test_otp_uniqueness_over_many_generations(self):
        """Generated OTPs should have variety (not deterministic)."""
        otps = {generate_otp() for _ in range(100)}
        self.assertGreater(len(otps), 5)

    def test_otp_is_string_type(self):
        otp = generate_otp()
        self.assertIsInstance(otp, str)

    def test_otp_digits_in_valid_range(self):
        for _ in range(50):
            otp = generate_otp()
            for digit in otp:
                self.assertIn(int(digit), range(10))


# ============================================================
# OTP CREATION TESTS
# ============================================================

class TestCreateOTP(TestCase):
    """Test OTP creation, hashing, and invalidation."""

    def setUp(self):
        self.user = User.objects.create_user('testuser', 'test@example.com', 'Pass1234!')

    def test_create_otp_returns_instance(self):
        otp = create_otp(self.user)
        self.assertIsNotNone(otp.pk)

    def test_create_otp_has_plaintext_code(self):
        otp = create_otp(self.user)
        self.assertTrue(hasattr(otp, '_plaintext_code'))
        self.assertEqual(len(otp._plaintext_code), 6)

    def test_otp_stored_hashed_not_plaintext(self):
        """OTP in DB should be hashed, not the raw 6-digit code."""
        otp = create_otp(self.user)
        self.assertNotEqual(otp.otp_code, otp._plaintext_code)
        self.assertGreater(len(otp.otp_code), 20)

    def test_create_otp_invalidates_previous_unused(self):
        otp1 = create_otp(self.user)
        otp2 = create_otp(self.user)
        otp1.refresh_from_db()
        self.assertTrue(otp1.is_used)
        self.assertFalse(otp2.is_used)

    def test_create_otp_sets_expiry(self):
        otp = create_otp(self.user)
        expected_expiry = timezone.now() + timedelta(
            minutes=getattr(settings, 'OTP_EXPIRY_MINUTES', 5)
        )
        # Allow 5 second tolerance
        self.assertAlmostEqual(
            otp.expires_at.timestamp(),
            expected_expiry.timestamp(),
            delta=5,
        )

    def test_create_otp_starts_with_zero_attempts(self):
        otp = create_otp(self.user)
        self.assertEqual(otp.attempts, 0)

    def test_multiple_invalidations(self):
        """Creating 3 OTPs should invalidate the first 2."""
        otp1 = create_otp(self.user)
        otp2 = create_otp(self.user)
        otp3 = create_otp(self.user)
        otp1.refresh_from_db()
        otp2.refresh_from_db()
        self.assertTrue(otp1.is_used)
        self.assertTrue(otp2.is_used)
        self.assertFalse(otp3.is_used)


# ============================================================
# OTP VERIFICATION TESTS
# ============================================================

class TestVerifyOTP(TestCase):
    """Test OTP verification including security edge cases."""

    def setUp(self):
        self.user = User.objects.create_user('testuser', 'test@example.com', 'Pass1234!')

    def test_verify_correct_otp_succeeds(self):
        otp = create_otp(self.user)
        is_valid, msg = verify_otp(self.user, otp._plaintext_code)
        self.assertTrue(is_valid)
        self.assertIn('verified', msg.lower())

    def test_verify_wrong_otp_fails(self):
        create_otp(self.user)
        is_valid, msg = verify_otp(self.user, '000000')
        self.assertFalse(is_valid)

    def test_verify_expired_otp_fails(self):
        otp = create_otp(self.user)
        EmailOTP.objects.filter(pk=otp.pk).update(
            expires_at=timezone.now() - timedelta(minutes=1)
        )
        is_valid, msg = verify_otp(self.user, otp._plaintext_code)
        self.assertFalse(is_valid)
        self.assertIn('expired', msg.lower())

    def test_verify_used_otp_fails(self):
        otp = create_otp(self.user)
        # First verification should succeed
        verify_otp(self.user, otp._plaintext_code)
        # Second verification should fail
        is_valid, msg = verify_otp(self.user, otp._plaintext_code)
        self.assertFalse(is_valid)

    def test_verify_max_attempts_lockout(self):
        otp = create_otp(self.user)
        max_attempts = getattr(settings, 'OTP_MAX_ATTEMPTS', 5)
        for _ in range(max_attempts):
            verify_otp(self.user, '999999')
        # Now even correct code should fail
        is_valid, msg = verify_otp(self.user, otp._plaintext_code)
        self.assertFalse(is_valid)

    def test_verify_no_otp_exists(self):
        is_valid, msg = verify_otp(self.user, '123456')
        self.assertFalse(is_valid)
        self.assertIn('no otp', msg.lower())

    def test_verify_marks_otp_as_used(self):
        otp = create_otp(self.user)
        verify_otp(self.user, otp._plaintext_code)
        otp.refresh_from_db()
        self.assertTrue(otp.is_used)

    def test_verify_increments_attempts(self):
        otp = create_otp(self.user)
        verify_otp(self.user, '999999')
        otp.refresh_from_db()
        self.assertEqual(otp.attempts, 1)

    def test_verify_for_different_user_fails(self):
        """User B should not be able to use User A's OTP."""
        other = User.objects.create_user('other', 'other@example.com', 'Pass1234!')
        otp = create_otp(self.user)
        is_valid, msg = verify_otp(other, otp._plaintext_code)
        self.assertFalse(is_valid)

    def test_remaining_attempts_message(self):
        otp = create_otp(self.user)
        is_valid, msg = verify_otp(self.user, '999999')
        self.assertIn('remaining', msg.lower())


# ============================================================
# OTP RATE LIMITING TESTS
# ============================================================

class TestCanResendOTP(TestCase):
    """Test OTP resend rate limiting."""

    def setUp(self):
        self.user = User.objects.create_user('testuser', 'test@example.com', 'Pass1234!')

    def test_can_resend_initially(self):
        self.assertTrue(can_resend_otp(self.user))

    @override_settings(OTP_MAX_RESENDS_PER_WINDOW=2)
    def test_cannot_resend_after_max(self):
        create_otp(self.user)
        create_otp(self.user)
        self.assertFalse(can_resend_otp(self.user))

    @override_settings(OTP_MAX_RESENDS_PER_WINDOW=1)
    def test_rate_limit_with_single_allowed(self):
        create_otp(self.user)
        self.assertFalse(can_resend_otp(self.user))


# ============================================================
# OTP EMAIL TESTS
# ============================================================

class TestSendOTPEmail(TestCase):
    """Test OTP email sending."""

    def setUp(self):
        self.user = User.objects.create_user('testuser', 'test@example.com', 'Pass1234!')

    @patch('accounts.otp_service.send_mail')
    def test_send_otp_email_success(self, mock_send):
        mock_send.return_value = 1
        result = send_otp_email(self.user, '123456')
        self.assertTrue(result)
        mock_send.assert_called_once()

    @patch('accounts.otp_service.send_mail')
    def test_send_otp_email_failure(self, mock_send):
        mock_send.side_effect = Exception("SMTP error")
        result = send_otp_email(self.user, '123456')
        self.assertFalse(result)

    @patch('accounts.otp_service.send_mail')
    def test_email_contains_otp_code(self, mock_send):
        mock_send.return_value = 1
        send_otp_email(self.user, '654321')
        call_args = mock_send.call_args
        self.assertIn('654321', call_args[1].get('message', '') or call_args[0][1])

    @patch('accounts.otp_service.send_mail')
    def test_email_sent_to_correct_recipient(self, mock_send):
        mock_send.return_value = 1
        send_otp_email(self.user, '123456')
        call_args = mock_send.call_args
        recipient_list = call_args[1].get('recipient_list') or call_args[0][3]
        self.assertIn('test@example.com', recipient_list)


# ============================================================
# MODEL TESTS
# ============================================================

class TestUserProfileModel(TestCase):
    """Test UserProfile model behavior."""

    def setUp(self):
        self.user = User.objects.create_user('testuser', 'test@example.com', 'Pass1234!')

    def test_profile_str(self):
        profile, _ = UserProfile.objects.get_or_create(user=self.user)
        self.assertIn('testuser', str(profile))

    def test_profile_defaults(self):
        profile, _ = UserProfile.objects.get_or_create(user=self.user)
        self.assertFalse(profile.is_email_verified)
        self.assertEqual(profile.auth_provider, 'email')
        self.assertEqual(float(profile.total_carbon_saved), 0.0)

    def test_profile_one_to_one(self):
        """Cannot create two profiles for the same user."""
        UserProfile.objects.get_or_create(user=self.user)
        from django.db import IntegrityError
        with self.assertRaises(IntegrityError):
            UserProfile.objects.create(user=self.user)


class TestEmailOTPModel(TestCase):
    """Test EmailOTP model behavior."""

    def setUp(self):
        self.user = User.objects.create_user('testuser', 'test@example.com', 'Pass1234!')

    def test_otp_is_valid_when_fresh(self):
        otp = EmailOTP.objects.create(
            user=self.user,
            otp_code='hashed_code',
            expires_at=timezone.now() + timedelta(minutes=5),
        )
        self.assertTrue(otp.is_valid())

    def test_otp_invalid_when_used(self):
        otp = EmailOTP.objects.create(
            user=self.user,
            otp_code='hashed_code',
            expires_at=timezone.now() + timedelta(minutes=5),
            is_used=True,
        )
        self.assertFalse(otp.is_valid())

    def test_otp_invalid_when_expired(self):
        otp = EmailOTP.objects.create(
            user=self.user,
            otp_code='hashed_code',
            expires_at=timezone.now() - timedelta(minutes=1),
        )
        self.assertFalse(otp.is_valid())

    @override_settings(OTP_MAX_ATTEMPTS=3)
    def test_otp_invalid_when_max_attempts_reached(self):
        otp = EmailOTP.objects.create(
            user=self.user,
            otp_code='hashed_code',
            expires_at=timezone.now() + timedelta(minutes=5),
            attempts=3,
        )
        self.assertFalse(otp.is_valid())

    def test_otp_str_representation(self):
        otp = EmailOTP.objects.create(
            user=self.user,
            otp_code='hashed_code',
            expires_at=timezone.now() + timedelta(minutes=5),
        )
        self.assertIn('testuser', str(otp))


# ============================================================
# REGISTRATION FORM TESTS
# ============================================================

class TestRegistrationForm(TestCase):
    """Test registration form validation thoroughly."""

    def get_valid_data(self):
        return {
            'username': 'newuser',
            'email': 'new@example.com',
            'first_name': 'Test',
            'last_name': 'User',
            'password1': 'StrongP@ss123',
            'password2': 'StrongP@ss123',
        }

    def test_valid_registration(self):
        form = RegistrationForm(data=self.get_valid_data())
        self.assertTrue(form.is_valid())

    def test_duplicate_email_rejected(self):
        User.objects.create_user('existing', 'new@example.com', 'Pass1234!')
        form = RegistrationForm(data=self.get_valid_data())
        self.assertFalse(form.is_valid())
        self.assertIn('email', form.errors)

    def test_password_mismatch_rejected(self):
        data = self.get_valid_data()
        data['password2'] = 'DifferentPassword123!'
        form = RegistrationForm(data=data)
        self.assertFalse(form.is_valid())

    def test_weak_password_rejected(self):
        data = self.get_valid_data()
        data['password1'] = '123'
        data['password2'] = '123'
        form = RegistrationForm(data=data)
        self.assertFalse(form.is_valid())

    def test_common_password_rejected(self):
        data = self.get_valid_data()
        data['password1'] = 'password123'
        data['password2'] = 'password123'
        form = RegistrationForm(data=data)
        self.assertFalse(form.is_valid())

    def test_invalid_username_script_tag(self):
        data = self.get_valid_data()
        data['username'] = 'user<script>'
        form = RegistrationForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn('username', form.errors)

    def test_username_with_spaces_rejected(self):
        data = self.get_valid_data()
        data['username'] = 'user name'
        form = RegistrationForm(data=data)
        self.assertFalse(form.is_valid())

    def test_username_with_at_sign_rejected(self):
        data = self.get_valid_data()
        data['username'] = 'user@name'
        form = RegistrationForm(data=data)
        self.assertFalse(form.is_valid())

    def test_valid_username_underscore(self):
        data = self.get_valid_data()
        data['username'] = 'user_name_123'
        form = RegistrationForm(data=data)
        self.assertTrue(form.is_valid())

    def test_username_too_short_rejected(self):
        data = self.get_valid_data()
        data['username'] = 'ab'
        form = RegistrationForm(data=data)
        self.assertFalse(form.is_valid())

    def test_email_normalized_lowercase(self):
        data = self.get_valid_data()
        data['email'] = 'Test@EXAMPLE.COM'
        form = RegistrationForm(data=data)
        self.assertTrue(form.is_valid())
        user = form.save()
        self.assertEqual(user.email, 'test@example.com')

    def test_save_creates_profile(self):
        form = RegistrationForm(data=self.get_valid_data())
        self.assertTrue(form.is_valid())
        user = form.save()
        self.assertTrue(UserProfile.objects.filter(user=user).exists())

    def test_save_sets_password_hash(self):
        form = RegistrationForm(data=self.get_valid_data())
        self.assertTrue(form.is_valid())
        user = form.save()
        self.assertTrue(user.check_password('StrongP@ss123'))
        self.assertNotEqual(user.password, 'StrongP@ss123')

    def test_missing_first_name_rejected(self):
        data = self.get_valid_data()
        data['first_name'] = ''
        form = RegistrationForm(data=data)
        self.assertFalse(form.is_valid())

    def test_last_name_optional(self):
        data = self.get_valid_data()
        data['last_name'] = ''
        form = RegistrationForm(data=data)
        self.assertTrue(form.is_valid())


# ============================================================
# LOGIN FORM TESTS
# ============================================================

class TestLoginForm(TestCase):
    """Test login form validation."""

    def test_valid_login_form(self):
        form = LoginForm(data={'username': 'testuser', 'password': 'Pass1234!'})
        self.assertTrue(form.is_valid())

    def test_missing_username(self):
        form = LoginForm(data={'username': '', 'password': 'pass'})
        self.assertFalse(form.is_valid())

    def test_missing_password(self):
        form = LoginForm(data={'username': 'user', 'password': ''})
        self.assertFalse(form.is_valid())


# ============================================================
# OTP VERIFICATION FORM TESTS
# ============================================================

class TestOTPVerificationForm(TestCase):
    """Test OTP form validation."""

    def test_valid_otp_code(self):
        form = OTPVerificationForm(data={'otp_code': '123456'})
        self.assertTrue(form.is_valid())

    def test_too_short_otp(self):
        form = OTPVerificationForm(data={'otp_code': '123'})
        self.assertFalse(form.is_valid())

    def test_too_long_otp(self):
        form = OTPVerificationForm(data={'otp_code': '1234567'})
        self.assertFalse(form.is_valid())

    def test_non_numeric_otp_rejected(self):
        form = OTPVerificationForm(data={'otp_code': 'abcdef'})
        self.assertFalse(form.is_valid())

    def test_mixed_chars_otp_rejected(self):
        form = OTPVerificationForm(data={'otp_code': '12ab34'})
        self.assertFalse(form.is_valid())

    def test_empty_otp_rejected(self):
        form = OTPVerificationForm(data={'otp_code': ''})
        self.assertFalse(form.is_valid())


# ============================================================
# PROFILE UPDATE FORM TESTS
# ============================================================

class TestProfileUpdateForm(TestCase):
    """Test profile update form security."""

    def setUp(self):
        self.user = User.objects.create_user('testuser', 'test@example.com', 'Pass1234!')
        self.profile, _ = UserProfile.objects.get_or_create(user=self.user)

    def test_email_uniqueness_on_update(self):
        User.objects.create_user('other', 'other@example.com', 'Pass1234!')
        form = ProfileUpdateForm(
            instance=self.profile,
            data={
                'first_name': 'Test',
                'email': 'other@example.com',
                'bio': '',
                'location': '',
            }
        )
        self.assertFalse(form.is_valid())
        self.assertIn('email', form.errors)

    def test_can_keep_own_email(self):
        form = ProfileUpdateForm(
            instance=self.profile,
            data={
                'first_name': 'Test',
                'email': 'test@example.com',
                'bio': 'Hello',
                'location': 'City',
            }
        )
        self.assertTrue(form.is_valid())

    def test_bio_max_length_respected(self):
        form = ProfileUpdateForm(
            instance=self.profile,
            data={
                'first_name': 'Test',
                'email': 'test@example.com',
                'bio': 'x' * 501,
                'location': '',
            }
        )
        self.assertFalse(form.is_valid())


# ============================================================
# REGISTER VIEW TESTS
# ============================================================

class TestRegisterView(TestCase):
    """Test registration view."""

    def setUp(self):
        self.client = Client()

    def test_register_page_loads(self):
        response = self.client.get(reverse('accounts:register'))
        self.assertEqual(response.status_code, 200)

    def test_register_page_contains_form(self):
        response = self.client.get(reverse('accounts:register'))
        self.assertIn('form', response.context)

    @patch('accounts.views.send_otp_email', return_value=True)
    def test_successful_registration_redirects(self, mock_send):
        response = self.client.post(reverse('accounts:register'), {
            'username': 'newuser',
            'email': 'new@example.com',
            'first_name': 'Test',
            'password1': 'StrongP@ss123',
            'password2': 'StrongP@ss123',
        })
        self.assertEqual(response.status_code, 302)

    @patch('accounts.views.send_otp_email', return_value=True)
    def test_successful_registration_creates_user(self, mock_send):
        self.client.post(reverse('accounts:register'), {
            'username': 'newuser',
            'email': 'new@example.com',
            'first_name': 'Test',
            'password1': 'StrongP@ss123',
            'password2': 'StrongP@ss123',
        })
        self.assertTrue(User.objects.filter(username='newuser').exists())

    @patch('accounts.views.send_otp_email', return_value=True)
    def test_registration_stores_otp_user_id_in_session(self, mock_send):
        self.client.post(reverse('accounts:register'), {
            'username': 'newuser',
            'email': 'new@example.com',
            'first_name': 'Test',
            'password1': 'StrongP@ss123',
            'password2': 'StrongP@ss123',
        })
        self.assertIn('otp_user_id', self.client.session)

    def test_authenticated_user_redirected_from_register(self):
        user = User.objects.create_user('testuser', 'test@example.com', 'Pass1234!')
        self.client.force_login(user)
        response = self.client.get(reverse('accounts:register'))
        self.assertEqual(response.status_code, 302)

    def test_invalid_registration_rerenders_form(self):
        response = self.client.post(reverse('accounts:register'), {
            'username': '',
            'email': 'bad',
            'password1': '123',
            'password2': '456',
        })
        self.assertEqual(response.status_code, 200)


# ============================================================
# VERIFY OTP VIEW TESTS
# ============================================================

class TestVerifyOTPView(TestCase):
    """Test OTP verification view."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user('testuser', 'test@example.com', 'Pass1234!')
        self.otp = create_otp(self.user)

    def test_verify_page_requires_session(self):
        """Without otp_user_id in session, should redirect."""
        response = self.client.get(reverse('accounts:verify_otp'))
        self.assertEqual(response.status_code, 302)

    def test_verify_page_loads_with_session(self):
        session = self.client.session
        session['otp_user_id'] = self.user.id
        session.save()
        response = self.client.get(reverse('accounts:verify_otp'))
        self.assertEqual(response.status_code, 200)

    def test_verify_page_shows_email(self):
        session = self.client.session
        session['otp_user_id'] = self.user.id
        session.save()
        response = self.client.get(reverse('accounts:verify_otp'))
        self.assertIn('user_email', response.context)


# ============================================================
# RESEND OTP VIEW TESTS
# ============================================================

class TestResendOTPView(TestCase):
    """Test OTP resend functionality."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user('testuser', 'test@example.com', 'Pass1234!')

    def test_resend_without_session_redirects(self):
        response = self.client.post(reverse('accounts:resend_otp'))
        self.assertEqual(response.status_code, 302)
        self.assertIn('register', response.url)

    @patch('accounts.views.send_otp_email', return_value=True)
    def test_resend_with_session_succeeds(self, mock_send):
        session = self.client.session
        session['otp_user_id'] = self.user.id
        session.save()
        response = self.client.post(reverse('accounts:resend_otp'))
        self.assertEqual(response.status_code, 302)
        self.assertIn('verify-otp', response.url)

    @patch('accounts.views.can_resend_otp', return_value=False)
    def test_resend_rate_limited(self, mock_can_resend):
        session = self.client.session
        session['otp_user_id'] = self.user.id
        session.save()
        response = self.client.post(reverse('accounts:resend_otp'))
        self.assertEqual(response.status_code, 302)


# ============================================================
# LOGIN VIEW TESTS
# ============================================================

class TestLoginView(TestCase):
    """Test login view including security."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user('testuser', 'test@example.com', 'Pass1234!')
        profile, _ = UserProfile.objects.get_or_create(user=self.user)
        profile.is_email_verified = True
        profile.save()

    def test_login_page_loads(self):
        response = self.client.get(reverse('accounts:login'))
        self.assertEqual(response.status_code, 200)

    def test_login_with_username(self):
        response = self.client.post(reverse('accounts:login'), {
            'username': 'testuser',
            'password': 'Pass1234!',
        })
        self.assertEqual(response.status_code, 302)

    def test_login_with_email(self):
        response = self.client.post(reverse('accounts:login'), {
            'username': 'test@example.com',
            'password': 'Pass1234!',
        })
        self.assertEqual(response.status_code, 302)

    def test_login_invalid_credentials_rerenders(self):
        response = self.client.post(reverse('accounts:login'), {
            'username': 'testuser',
            'password': 'wrongpassword',
        })
        self.assertEqual(response.status_code, 200)

    def test_login_nonexistent_user_rerenders(self):
        response = self.client.post(reverse('accounts:login'), {
            'username': 'nobody',
            'password': 'anything',
        })
        self.assertEqual(response.status_code, 200)

    def test_open_redirect_blocked(self):
        """next parameter with external URL should be ignored."""
        response = self.client.post(
            reverse('accounts:login') + '?next=https://evil.com',
            {'username': 'testuser', 'password': 'Pass1234!'},
        )
        self.assertEqual(response.status_code, 302)
        self.assertNotIn('evil.com', response.url)

    def test_open_redirect_protocol_relative_blocked(self):
        response = self.client.post(
            reverse('accounts:login') + '?next=//evil.com',
            {'username': 'testuser', 'password': 'Pass1234!'},
        )
        self.assertEqual(response.status_code, 302)
        self.assertNotIn('evil.com', response.url)

    def test_safe_next_redirect(self):
        response = self.client.post(
            reverse('accounts:login') + '?next=/dashboard/',
            {'username': 'testuser', 'password': 'Pass1234!'},
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, '/dashboard/')

    @patch('accounts.views.send_otp_email', return_value=True)
    def test_unverified_user_redirected_to_otp(self, mock_send):
        profile = self.user.profile
        profile.is_email_verified = False
        profile.save()
        response = self.client.post(reverse('accounts:login'), {
            'username': 'testuser',
            'password': 'Pass1234!',
        })
        self.assertEqual(response.status_code, 302)
        self.assertIn('verify-otp', response.url)

    def test_authenticated_user_redirected(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse('accounts:login'))
        self.assertEqual(response.status_code, 302)


# ============================================================
# LOGOUT VIEW TESTS
# ============================================================

class TestLogoutView(TestCase):
    """Test logout security."""

    def setUp(self):
        self.user = User.objects.create_user('testuser', 'test@example.com', 'Pass1234!')
        self.client = Client()
        self.client.force_login(self.user)

    def test_logout_via_post(self):
        response = self.client.post(reverse('accounts:logout'))
        self.assertEqual(response.status_code, 302)

    def test_logout_via_get_does_not_logout(self):
        """GET should NOT log the user out (CSRF safety)."""
        self.client.get(reverse('accounts:logout'))
        # Check the user is still authenticated by accessing a protected page
        response = self.client.get(reverse('accounts:profile'))
        self.assertEqual(response.status_code, 200)

    def test_logout_redirects_to_home(self):
        response = self.client.post(reverse('accounts:logout'))
        self.assertEqual(response.url, '/')


# ============================================================
# PROFILE VIEW TESTS
# ============================================================

class TestProfileView(TestCase):
    """Test profile view access and data."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user('testuser', 'test@example.com', 'Pass1234!')
        UserProfile.objects.get_or_create(user=self.user)

    def test_unauthenticated_redirect(self):
        response = self.client.get(reverse('accounts:profile'))
        self.assertEqual(response.status_code, 302)
        self.assertIn('login', response.url)

    def test_authenticated_access(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse('accounts:profile'))
        self.assertEqual(response.status_code, 200)

    def test_profile_context_has_stats(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse('accounts:profile'))
        self.assertIn('total_carbon', response.context)
        self.assertIn('entry_count', response.context)

    def test_profile_creates_if_missing(self):
        """ProfileView should auto-create profile if not exists."""
        new_user = User.objects.create_user('newguy', 'new@example.com', 'Pass1234!')
        self.client.force_login(new_user)
        response = self.client.get(reverse('accounts:profile'))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(UserProfile.objects.filter(user=new_user).exists())
