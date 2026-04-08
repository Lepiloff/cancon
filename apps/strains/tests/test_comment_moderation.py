from unittest.mock import MagicMock, patch

from openai import OpenAIError
from django.test import SimpleTestCase, override_settings

from apps.strains.comment_moderation import moderate_strain_comment


class CommentModerationTest(SimpleTestCase):
    def test_local_profanity_is_rejected_without_provider_call(self):
        result = moderate_strain_comment('This is fucking strong', '')

        self.assertEqual(result.status, 'rejected')
        self.assertEqual(result.reason, 'local_profanity_match')

    @patch('apps.strains.comment_moderation.TranslationConfig.OPENAI_API_KEY', 'test-key')
    @patch('apps.strains.comment_moderation.create_chat_completion')
    @patch('apps.strains.comment_moderation.OpenAI')
    def test_provider_approved_response(self, mocked_openai, mocked_completion):
        mocked_completion.return_value = MagicMock(
            choices=[MagicMock(message=MagicMock(content='{"status":"approved","reason":"clean"}'))]
        )

        result = moderate_strain_comment('Relaxing body effect', 'A little dry')

        self.assertEqual(result.status, 'approved')
        self.assertEqual(result.reason, 'clean')
        mocked_openai.assert_called_once()

    @patch('apps.strains.comment_moderation.TranslationConfig.OPENAI_API_KEY', 'test-key')
    @patch('apps.strains.comment_moderation.create_chat_completion', side_effect=OpenAIError('boom'))
    @patch('apps.strains.comment_moderation.OpenAI')
    def test_provider_error_marks_comment_pending(self, mocked_openai, _mocked_completion):
        result = moderate_strain_comment('Relaxing body effect', 'A little dry')

        self.assertEqual(result.status, 'pending')
        self.assertEqual(result.reason, 'provider_error')
        mocked_openai.assert_called_once()
