'use strict';

/* ============================================
   CARBONTRACK — Firebase Authentication
   Client-side Google & GitHub sign-in
   ============================================ */

(function initFirebaseAuth() {
    const body = document.body;
    const apiKey = body.dataset.firebaseApiKey;
    const authDomain = body.dataset.firebaseAuthDomain;
    const projectId = body.dataset.firebaseProjectId;

    // Skip initialization if Firebase config is not set
    if (!apiKey || !authDomain || !projectId) {
        console.info('Firebase config not found. Social login disabled.');
        disableSocialButtons();
        return;
    }

    // Firebase config
    const firebaseConfig = {
        apiKey: apiKey,
        authDomain: authDomain,
        projectId: projectId,
    };

    // Initialize Firebase (compat mode loaded via CDN in base.html)
    try {
        if (typeof firebase !== 'undefined') {
            if (!firebase.apps.length) {
                firebase.initializeApp(firebaseConfig);
            }
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

    // ---- CSRF Token ----
    function getCookie(name) {
        let val = null;
        if (document.cookie) {
            document.cookie.split(';').forEach(function(c) {
                c = c.trim();
                if (c.startsWith(name + '=')) {
                    val = decodeURIComponent(c.substring(name.length + 1));
                }
            });
        }
        return val;
    }

    // ---- Send ID Token to Django Backend ----
    function sendTokenToBackend(idToken) {
        const csrftoken = getCookie('csrftoken');
        
        return fetch('/accounts/firebase-login/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrftoken,
            },
            body: JSON.stringify({ id_token: idToken }),
            credentials: 'same-origin',
        })
        .then(function(response) { return response.json(); })
        .then(function(data) {
            if (data.success) {
                window.location.href = data.redirect_url || '/dashboard/';
            } else {
                showError(data.error || 'Authentication failed. Please try again.');
            }
        })
        .catch(function(err) {
            console.error('Backend auth error:', err);
            showError('Connection error. Please try again.');
        });
    }

    // ---- Google Sign-In ----
    function signInWithGoogle() {
        const provider = new firebase.auth.GoogleAuthProvider();
        provider.addScope('email');
        provider.addScope('profile');

        showLoading(true);
        firebase.auth().signInWithPopup(provider)
            .then(function(result) {
                return result.user.getIdToken();
            })
            .then(function(idToken) {
                return sendTokenToBackend(idToken);
            })
            .catch(function(error) {
                console.error('Google sign-in error:', error);
                if (error.code !== 'auth/popup-closed-by-user') {
                    showError('Google sign-in failed: ' + error.message);
                }
            })
            .finally(function() {
                showLoading(false);
            });
    }

    // ---- GitHub Sign-In ----
    function signInWithGitHub() {
        const provider = new firebase.auth.GithubAuthProvider();
        provider.addScope('user:email');

        showLoading(true);
        firebase.auth().signInWithPopup(provider)
            .then(function(result) {
                return result.user.getIdToken();
            })
            .then(function(idToken) {
                return sendTokenToBackend(idToken);
            })
            .catch(function(error) {
                console.error('GitHub sign-in error:', error);
                if (error.code !== 'auth/popup-closed-by-user') {
                    showError('GitHub sign-in failed: ' + error.message);
                }
            })
            .finally(function() {
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
        // Try to add an error message to the page
        let container = document.querySelector('.auth-card') || document.querySelector('.card');
        if (container) {
            const existing = container.querySelector('.firebase-error');
            if (existing) existing.remove();

            const errDiv = document.createElement('div');
            errDiv.className = 'message message-error firebase-error';
            errDiv.textContent = message;
            errDiv.style.marginBottom = '16px';
            container.prepend(errDiv);

            setTimeout(function() { errDiv.remove(); }, 5000);
        }
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
