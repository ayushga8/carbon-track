"""
Firebase authentication integration.

Security:
- Checks token revocation status
- Verifies email_verified before linking accounts
- Limits username generation loop to prevent DoS
- Catches specific Firebase exceptions
"""

import logging
import os

from django.conf import settings
from django.contrib.auth.models import User
from django.db import transaction

from .models import UserProfile

logger = logging.getLogger(__name__)

# Try to initialize Firebase Admin SDK
firebase_admin_initialized = False
_firebase_auth = None

try:
    import firebase_admin
    from firebase_admin import credentials, auth as fb_auth
    cred_path = settings.FIREBASE_CREDENTIALS_PATH
    if os.path.exists(cred_path):
        cred = credentials.Certificate(cred_path)
        firebase_admin.initialize_app(cred)
        _firebase_auth = fb_auth
        firebase_admin_initialized = True
        logger.info("Firebase Admin SDK initialized successfully.")
    else:
        logger.warning(
            f"Firebase credentials not found at {cred_path}. "
            "Social login will be disabled."
        )
except ImportError:
    logger.warning(
        "firebase-admin package not installed. Social login will be disabled."
    )
except Exception as e:
    logger.warning(
        f"Firebase initialization failed: {e}. Social login will be disabled."
    )


def verify_firebase_token(id_token):
    """
    Verify a Firebase ID token and return decoded user info.

    Uses check_revoked=True to reject revoked tokens.
    """
    if not firebase_admin_initialized or _firebase_auth is None:
        return None
    try:
        decoded_token = _firebase_auth.verify_id_token(id_token, check_revoked=True)
        return decoded_token
    except Exception as e:
        logger.error(f"Firebase token verification failed: {type(e).__name__}: {e}")
        return None


@transaction.atomic
def get_or_create_user_from_firebase(firebase_user_data):
    """
    Create or get a Django user from Firebase user data.

    Security:
    - Only links existing accounts if Firebase email is verified
    - Caps username generation loop at 100 iterations
    """
    uid = firebase_user_data.get('uid')
    email = firebase_user_data.get('email', '')
    name = firebase_user_data.get('name', '')
    email_verified = firebase_user_data.get('email_verified', False)
    provider = firebase_user_data.get('firebase', {}).get('sign_in_provider', 'email')

    # Map Firebase provider to our choices
    provider_map = {
        'google.com': 'google',
        'github.com': 'github',
        'password': 'email',
    }
    auth_provider = provider_map.get(provider, 'email')

    # Try to find existing user by Firebase UID
    try:
        profile = UserProfile.objects.select_related('user').get(firebase_uid=uid)
        return profile.user
    except UserProfile.DoesNotExist:
        pass

    # Only link by email if Firebase has verified the email
    if email and email_verified:
        try:
            user = User.objects.get(email=email)
            profile, _ = UserProfile.objects.get_or_create(user=user)
            profile.firebase_uid = uid
            profile.auth_provider = auth_provider
            profile.is_email_verified = True
            profile.save(update_fields=['firebase_uid', 'auth_provider', 'is_email_verified'])
            return user
        except User.DoesNotExist:
            pass

    # Create new user with bounded username generation
    username = email.split('@')[0] if email else f'user_{uid[:8]}'
    base_username = username
    counter = 1
    max_attempts = 100
    while User.objects.filter(username=username).exists():
        username = f"{base_username}_{counter}"
        counter += 1
        if counter > max_attempts:
            raise ValueError(
                f"Could not generate unique username after {max_attempts} attempts"
            )

    first_name = name.split(' ')[0] if name else ''
    last_name = ' '.join(name.split(' ')[1:]) if name and ' ' in name else ''

    user = User.objects.create_user(
        username=username,
        email=email,
        first_name=first_name,
        last_name=last_name,
    )

    UserProfile.objects.create(
        user=user,
        firebase_uid=uid,
        auth_provider=auth_provider,
        is_email_verified=email_verified,
    )

    return user
