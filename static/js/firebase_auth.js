'use strict';

/* ============================================
   CARBONTRACK — Firebase Authentication
   Client-side Google & GitHub sign-in
   Uses signInWithPopup for reliable auth
   ============================================ */

(function initFirebaseAuth() {
    var body = document.body;
    var apiKey = body.dataset.firebaseApiKey;
    var authDomain = body.dataset.firebaseAuthDomain;
    var projectId = body.dataset.firebaseProjectId;

    // Skip initialization if Firebase config is not set
    if (!apiKey || !authDomain || !projectId) {
        console.info('Firebase config not found. Social login disabled.');
        disableSocialButtons();
        return;
    }

    console.log('Firebase: Initializing with project', projectId);

    // Firebase config
    var firebaseConfig = {
        apiKey: apiKey,
        authDomain: authDomain,
        projectId: projectId,
    };

    // Initialize Firebase
    try {
        if (typeof firebase !== 'undefined') {
            if (!firebase.apps.length) {
                firebase.initializeApp(firebaseConfig);
            }
            console.log('Firebase: SDK initialized successfully');
        } else {
            console.warn('Firebase SDK not loaded. Social login disabled.');
            disableSocialButtons();
            return;
        }
    } catch (err) {
        console.error('Firebase initialization error:', err);
        disableSocialButtons();
        return;
    }

    // ---- Send ID Token to Django Backend ----
    function sendTokenToBackend(idToken) {
        console.log('Firebase: Sending token to backend...');

        return fetch('/accounts/firebase-login/', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ id_token: idToken }),
            credentials: 'same-origin',
        })
        .then(function(response) {
            console.log('Firebase: Backend response status:', response.status);
            return response.json();
        })
        .then(function(data) {
            if (data.success) {
                console.log('Firebase: Login successful, redirecting...');
                window.location.href = data.redirect_url || '/dashboard/';
            } else {
                console.error('Firebase: Backend error:', data.error);
                showError(data.error || 'Authentication failed. Please try again.');
                showLoading(false);
            }
        })
        .catch(function(err) {
            console.error('Firebase: Network error:', err);
            showError('Connection error. Please try again.');
            showLoading(false);
        });
    }

    // ---- Handle popup sign-in result ----
    function handlePopupResult(result) {
        console.log('Firebase: handlePopupResult called', result);
        if (result && result.user) {
            console.log('Firebase: Popup sign-in successful for', result.user.email);
            return result.user.getIdToken(true).then(function(idToken) {
                console.log('Firebase: Got ID token, length:', idToken.length);
                return sendTokenToBackend(idToken);
            }).catch(function(err) {
                console.error('Firebase: Failed to get ID token:', err);
                showError('Failed to get authentication token. Please try again.');
                showLoading(false);
            });
        } else {
            console.warn('Firebase: No user in popup result');
            showLoading(false);
        }
    }

    // ---- Google Sign-In (using popup) ----
    function signInWithGoogle() {
        var provider = new firebase.auth.GoogleAuthProvider();
        provider.addScope('email');
        provider.addScope('profile');

        console.log('Firebase: Starting Google sign-in popup...');
        showLoading(true);

        firebase.auth().signInWithPopup(provider)
            .then(handlePopupResult)
            .catch(function(error) {
                console.error('Firebase Google sign-in error:', error.code, error.message);
                if (error.code === 'auth/popup-closed-by-user') {
                    console.log('Firebase: User closed the sign-in popup.');
                } else if (error.code === 'auth/popup-blocked') {
                    showError('Popup was blocked by your browser. Please allow popups for this site.');
                } else {
                    showError('Google sign-in failed: ' + error.message);
                }
                showLoading(false);
            });
    }

    // ---- GitHub Sign-In (using popup) ----
    function signInWithGitHub() {
        var provider = new firebase.auth.GithubAuthProvider();
        provider.addScope('user:email');

        console.log('Firebase: Starting GitHub sign-in popup...');
        showLoading(true);

        firebase.auth().signInWithPopup(provider)
            .then(handlePopupResult)
            .catch(function(error) {
                console.error('Firebase GitHub sign-in error:', error.code, error.message);
                if (error.code === 'auth/popup-closed-by-user') {
                    console.log('Firebase: User closed the sign-in popup.');
                } else if (error.code === 'auth/popup-blocked') {
                    showError('Popup was blocked by your browser. Please allow popups for this site.');
                } else if (error.code === 'auth/account-exists-with-different-credential') {
                    showError('An account already exists with this email using a different sign-in method.');
                } else {
                    showError('GitHub sign-in failed: ' + error.message);
                }
                showLoading(false);
            });
    }

    // ---- UI Helpers ----
    function showLoading(show) {
        document.querySelectorAll('.social-btn').forEach(function(btn) {
            btn.disabled = show;
            if (show) {
                btn.dataset.originalText = btn.textContent;
                btn.textContent = 'Signing in...';
            } else if (btn.dataset.originalText) {
                btn.textContent = btn.dataset.originalText;
            }
        });
    }

    function showError(message) {
        var container = document.querySelector('.auth-card') || document.querySelector('.card');
        if (container) {
            var existing = container.querySelector('.firebase-error');
            if (existing) existing.remove();

            var errDiv = document.createElement('div');
            errDiv.className = 'message message-error firebase-error';
            errDiv.textContent = message;
            errDiv.style.marginBottom = '16px';
            container.prepend(errDiv);

            setTimeout(function() { errDiv.remove(); }, 8000);
        }
        // Always log to console as well
        console.error('Firebase UI Error:', message);
    }

    function disableSocialButtons() {
        document.querySelectorAll('.social-btn').forEach(function(btn) {
            btn.style.opacity = '0.5';
            btn.style.pointerEvents = 'none';
            btn.title = 'Social login is not configured';
        });
    }

    // ---- Bind Events ----
    document.querySelectorAll('.google-btn').forEach(function(btn) {
        btn.addEventListener('click', function(e) {
            e.preventDefault();
            signInWithGoogle();
        });
    });

    document.querySelectorAll('.github-btn').forEach(function(btn) {
        btn.addEventListener('click', function(e) {
            e.preventDefault();
            signInWithGitHub();
        });
    });
})();
