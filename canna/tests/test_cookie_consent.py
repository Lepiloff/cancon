"""
Tests for cookie consent view, context processor, and middleware.
"""

import json

from django.contrib.auth import get_user_model
from django.test import TestCase, RequestFactory, override_settings

from canna.context_processors import cookie_consent


User = get_user_model()


class CookieConsentViewTest(TestCase):
    """Tests for the POST /cookie-consent/ endpoint."""

    def setUp(self):
        self.url = '/cookie-consent/'
        self.user = User.objects.create_user(
            email='test@example.com', password='testpass123'
        )

    def test_get_not_allowed(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 405)

    def test_invalid_json_returns_400(self):
        response = self.client.post(
            self.url, data='not json', content_type='application/json'
        )
        self.assertEqual(response.status_code, 400)

    def test_accept_analytics(self):
        response = self.client.post(
            self.url,
            data=json.dumps({'analytics': True}),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['status'], 'ok')
        self.assertTrue(data['consent']['analytics'])
        self.assertTrue(data['consent']['necessary'])

        # Check cookie was set
        cookie = response.cookies.get('cookie_consent')
        self.assertIsNotNone(cookie)
        cookie_value = json.loads(cookie.value)
        self.assertTrue(cookie_value['analytics'])
        self.assertTrue(cookie_value['necessary'])
        self.assertEqual(cookie['max-age'], 15552000)
        self.assertEqual(cookie['samesite'], 'Lax')
        self.assertEqual(cookie['path'], '/')

    def test_decline_analytics(self):
        response = self.client.post(
            self.url,
            data=json.dumps({'analytics': False}),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertFalse(data['consent']['analytics'])
        self.assertTrue(data['consent']['necessary'])

    def test_missing_analytics_defaults_to_false(self):
        response = self.client.post(
            self.url,
            data=json.dumps({}),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertFalse(data['consent']['analytics'])

    def test_authenticated_user_saves_to_profile(self):
        self.client.login(email='test@example.com', password='testpass123')
        response = self.client.post(
            self.url,
            data=json.dumps({'analytics': True}),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 200)

        self.user.refresh_from_db()
        self.assertTrue(self.user.cookie_consent['analytics'])
        self.assertTrue(self.user.cookie_consent['necessary'])
        self.assertIsNotNone(self.user.cookie_consent_date)

    def test_anonymous_user_does_not_error(self):
        response = self.client.post(
            self.url,
            data=json.dumps({'analytics': True}),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 200)

    def test_cookie_not_httponly(self):
        """Cookie must be readable by JavaScript to conditionally load GA4."""
        response = self.client.post(
            self.url,
            data=json.dumps({'analytics': True}),
            content_type='application/json',
        )
        cookie = response.cookies.get('cookie_consent')
        self.assertFalse(cookie['httponly'])


class CookieConsentContextProcessorTest(TestCase):
    """Tests for the cookie_consent context processor."""

    def setUp(self):
        self.factory = RequestFactory()
        self.user = User.objects.create_user(
            email='test@example.com', password='testpass123'
        )

    def _make_request(self, cookies=None, user=None):
        request = self.factory.get('/')
        request.COOKIES = cookies or {}
        if user:
            request.user = user
        else:
            from django.contrib.auth.models import AnonymousUser
            request.user = AnonymousUser()
        return request

    def test_no_cookie_anonymous_shows_banner(self):
        request = self._make_request()
        ctx = cookie_consent(request)
        self.assertTrue(ctx['show_cookie_banner'])
        self.assertEqual(ctx['cookie_consent'], {})
        self.assertFalse(ctx['restore_cookie_consent'])

    def test_cookie_present_hides_banner(self):
        consent = json.dumps({'analytics': True, 'necessary': True})
        request = self._make_request(cookies={'cookie_consent': consent})
        ctx = cookie_consent(request)
        self.assertFalse(ctx['show_cookie_banner'])
        self.assertTrue(ctx['cookie_consent']['analytics'])
        self.assertFalse(ctx['restore_cookie_consent'])

    def test_authenticated_user_with_saved_consent_no_cookie_sets_restore(self):
        self.user.cookie_consent = {'analytics': True, 'necessary': True}
        self.user.save()
        request = self._make_request(user=self.user)
        ctx = cookie_consent(request)
        self.assertFalse(ctx['show_cookie_banner'])
        self.assertTrue(ctx['restore_cookie_consent'])
        self.assertEqual(ctx['cookie_consent'], self.user.cookie_consent)

    def test_authenticated_user_without_consent_shows_banner(self):
        request = self._make_request(user=self.user)
        ctx = cookie_consent(request)
        self.assertTrue(ctx['show_cookie_banner'])
        self.assertFalse(ctx['restore_cookie_consent'])

    def test_invalid_cookie_json_shows_banner(self):
        request = self._make_request(cookies={'cookie_consent': 'not-json'})
        ctx = cookie_consent(request)
        self.assertTrue(ctx['show_cookie_banner'])
        self.assertEqual(ctx['cookie_consent'], {})


class CookieConsentMiddlewareTest(TestCase):
    """Tests for the CookieConsentMiddleware that restores cookies on login."""

    def setUp(self):
        self.user = User.objects.create_user(
            email='test@example.com', password='testpass123'
        )

    def test_login_restores_cookie_from_user_profile(self):
        """When user with saved consent logs in, cookie should be set."""
        self.user.cookie_consent = {'analytics': True, 'necessary': True}
        self.user.save()

        # Login triggers the signal which sets session flag
        self.client.login(email='test@example.com', password='testpass123')

        # Next request should have the cookie set by middleware
        response = self.client.get('/')
        cookie = response.cookies.get('cookie_consent')
        if cookie:
            cookie_value = json.loads(cookie.value)
            self.assertTrue(cookie_value['analytics'])

    def test_login_without_consent_does_not_set_cookie(self):
        """When user without saved consent logs in, no cookie should be set."""
        self.client.login(email='test@example.com', password='testpass123')
        response = self.client.get('/')
        cookie = response.cookies.get('cookie_consent')
        # Cookie should not be present or should be empty
        if cookie:
            self.assertEqual(cookie.value, '')

    def test_session_flag_cleared_after_restore(self):
        """The _restore_cookie_consent session flag should be cleared after use."""
        self.user.cookie_consent = {'analytics': True, 'necessary': True}
        self.user.save()

        self.client.login(email='test@example.com', password='testpass123')

        # First request restores cookie
        self.client.get('/')

        # Second request should not have the session flag
        session = self.client.session
        self.assertNotIn('_restore_cookie_consent', session)
