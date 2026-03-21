"""
Signals for the users app.
"""
from django.contrib.auth.signals import user_logged_in


def restore_cookie_consent_on_login(sender, user, request, **kwargs):
    """
    When a user logs in, store their saved cookie consent preferences
    in the session so the CookieConsentMiddleware can set the cookie
    on the response.
    """
    if user.cookie_consent:
        request.session['_restore_cookie_consent'] = user.cookie_consent


user_logged_in.connect(restore_cookie_consent_on_login)
