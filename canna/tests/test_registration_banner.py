import json

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse


User = get_user_model()


class RegistrationBannerFunnelTest(TestCase):
    def setUp(self):
        self.signup_user = User.objects.create_user(
            email='banner@example.com',
            password='testpass123',
        )

    def _set_cookie_consent(self):
        self.client.cookies['cookie_consent'] = json.dumps(
            {'analytics': False, 'necessary': True}
        )

    def test_no_banner_on_first_qualifying_landing_page(self):
        self._set_cookie_consent()

        response = self.client.get(
            reverse('main_page'),
            HTTP_REFERER='https://www.google.com/search?q=cannamente',
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context['show_registration_banner'])

    def test_banner_on_next_internal_page(self):
        self._set_cookie_consent()

        landing = self.client.get(
            reverse('main_page'),
            HTTP_REFERER='https://www.google.com/search?q=cannamente',
        )
        self.assertFalse(landing.context['show_registration_banner'])

        response = self.client.get(
            reverse('strain_list'),
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['show_registration_banner'])

    def test_banner_does_not_show_on_same_page_refresh(self):
        self._set_cookie_consent()

        landing = self.client.get(
            reverse('main_page'),
            HTTP_REFERER='https://www.google.com/search?q=cannamente',
        )
        self.assertFalse(landing.context['show_registration_banner'])

        refresh = self.client.get(reverse('main_page'))

        self.assertEqual(refresh.status_code, 200)
        self.assertFalse(refresh.context['show_registration_banner'])

    def test_no_banner_for_authenticated_users(self):
        self._set_cookie_consent()
        self.client.login(email='banner@example.com', password='testpass123')

        self.client.get(
            reverse('main_page'),
            HTTP_REFERER='https://www.google.com/search?q=cannamente',
        )
        response = self.client.get(
            reverse('strain_list'),
            HTTP_REFERER='http://testserver/',
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context['show_registration_banner'])

    def test_no_banner_when_cookie_banner_is_visible(self):
        self.client.get(
            reverse('main_page'),
            HTTP_REFERER='https://www.google.com/search?q=cannamente',
        )
        response = self.client.get(
            reverse('strain_list'),
            HTTP_REFERER='http://testserver/',
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context['show_registration_banner'])

    def test_dismiss_cookie_suppresses_banner(self):
        self._set_cookie_consent()
        self.client.cookies['reg_banner_dismissed'] = '1'

        self.client.get(
            reverse('main_page'),
            HTTP_REFERER='https://www.google.com/search?q=cannamente',
        )
        response = self.client.get(
            reverse('strain_list'),
            HTTP_REFERER='http://testserver/',
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context['show_registration_banner'])

    def test_search_bots_do_not_get_banner(self):
        self._set_cookie_consent()

        self.client.get(
            reverse('main_page'),
            HTTP_REFERER='https://www.google.com/search?q=cannamente',
            HTTP_USER_AGENT='Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)',
        )
        response = self.client.get(
            reverse('strain_list'),
            HTTP_REFERER='http://testserver/',
            HTTP_USER_AGENT='Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)',
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context['show_registration_banner'])


class RegistrationBannerDismissViewTest(TestCase):
    def test_dismiss_sets_cooldown_cookie(self):
        response = self.client.post(
            reverse('registration_banner_dismiss'),
            data='{}',
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 200)
        cookie = response.cookies.get('reg_banner_dismissed')
        self.assertIsNotNone(cookie)
        self.assertEqual(cookie.value, '1')
        self.assertEqual(cookie['max-age'], 604800)
        self.assertEqual(cookie['samesite'], 'Lax')
