"""
Tests for chat session ownership and routing behavior.
"""

from uuid import uuid4

from django.contrib.auth import get_user_model
from django.test import RequestFactory, TestCase
from django.urls import reverse

from apps.chat_bot.models import ChatSession
from apps.chat_bot.views import _get_reusable_chat_session


User = get_user_model()


class ChatSessionReuseTestCase(TestCase):
    """Tests for ownership-aware chat session reuse."""

    def setUp(self):
        self.factory = RequestFactory()
        self.owner = User.objects.create_user(
            email='owner@example.com',
            password='testpass123',
        )
        self.other_user = User.objects.create_user(
            email='other@example.com',
            password='testpass123',
        )

    def _request(self, user):
        request = self.factory.post('/api/chat/chat/')
        request.user = user
        return request

    def test_anonymous_user_can_reuse_same_ip_anonymous_session(self):
        session = ChatSession.objects.create(ip_address='10.0.0.1')

        reused = _get_reusable_chat_session(self._request(self._anonymous_user()), session.session_id, '10.0.0.1')

        self.assertEqual(reused, session)

    def test_anonymous_user_cannot_reuse_different_ip_anonymous_session(self):
        session = ChatSession.objects.create(ip_address='10.0.0.1')

        reused = _get_reusable_chat_session(self._request(self._anonymous_user()), session.session_id, '10.0.0.2')

        self.assertIsNone(reused)

    def test_anonymous_user_cannot_reuse_authenticated_session(self):
        session = ChatSession.objects.create(user=self.owner, ip_address='10.0.0.1')

        reused = _get_reusable_chat_session(self._request(self._anonymous_user()), session.session_id, '10.0.0.1')

        self.assertIsNone(reused)

    def test_authenticated_user_can_reuse_own_session(self):
        session = ChatSession.objects.create(user=self.owner, ip_address='10.0.0.1')

        reused = _get_reusable_chat_session(self._request(self.owner), session.session_id, '10.0.0.99')

        self.assertEqual(reused, session)

    def test_authenticated_user_cannot_reuse_other_users_session(self):
        session = ChatSession.objects.create(user=self.owner, ip_address='10.0.0.1')

        reused = _get_reusable_chat_session(self._request(self.other_user), session.session_id, '10.0.0.1')

        self.assertIsNone(reused)

    def test_authenticated_user_can_claim_same_ip_anonymous_session(self):
        session = ChatSession.objects.create(ip_address='10.0.0.1')

        reused = _get_reusable_chat_session(self._request(self.owner), session.session_id, '10.0.0.1')

        session.refresh_from_db()
        self.assertEqual(reused, session)
        self.assertEqual(session.user, self.owner)

    def test_invalid_session_id_returns_none(self):
        reused = _get_reusable_chat_session(self._request(self.owner), uuid4(), '10.0.0.1')
        self.assertIsNone(reused)

    @staticmethod
    def _anonymous_user():
        from django.contrib.auth.models import AnonymousUser

        return AnonymousUser()


class ChatRoutingTestCase(TestCase):
    """Tests for non-localized chat routing."""

    def test_chat_urls_are_not_language_prefixed(self):
        self.assertEqual(reverse('chat_bot:chat'), '/api/chat/chat/')
        self.assertEqual(reverse('chat_bot:stream'), '/api/chat/stream/')
