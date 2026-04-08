import json
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from apps.strains.factories import StrainFactory
from apps.strains.models import StrainComment


User = get_user_model()


class StrainCommentsViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            email='comments@example.com',
            password='testpass123',
        )
        self.strain = StrainFactory.create(active=True)

    def test_strain_detail_renders_first_approved_comments(self):
        approved = StrainComment.objects.create(
            user=self.user,
            strain=self.strain,
            pros='Relaxing',
            cons='Dry mouth',
            reaction='thumbs_up',
            status='approved',
        )
        StrainComment.objects.create(
            user=User.objects.create_user(email='pending@example.com', password='testpass123'),
            strain=self.strain,
            pros='Pending',
            cons='Pending',
            reaction='thumbs_down',
            status='pending',
        )

        response = self.client.get(reverse('strain_detail', args=[self.strain.slug]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, approved.pros)
        self.assertNotContains(response, 'Pending')
        self.assertEqual(response.context['approved_comments_count'], 1)

    def test_strain_detail_uses_public_display_name_without_email_leak(self):
        user = User.objects.create_user(
            email='privacycheck@example.com',
            password='testpass123',
        )
        StrainComment.objects.create(
            user=user,
            strain=self.strain,
            pros='Relaxing',
            cons='Dry mouth',
            reaction='thumbs_up',
            status='approved',
        )

        response = self.client.get(reverse('strain_detail', args=[self.strain.slug]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'pr***k')
        self.assertNotContains(response, 'privacycheck@example.com')

    def test_strain_detail_uses_explicit_display_name_when_present(self):
        user = User.objects.create_user(
            email='named@example.com',
            password='testpass123',
            display_name='Lucia',
        )
        StrainComment.objects.create(
            user=user,
            strain=self.strain,
            pros='Relaxing',
            cons='Dry mouth',
            reaction='thumbs_up',
            status='approved',
        )

        response = self.client.get(reverse('strain_detail', args=[self.strain.slug]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Lucia')
        self.assertNotContains(response, 'named@example.com')


class StrainCommentsApiTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            email='api-comments@example.com',
            password='testpass123',
        )
        self.strain = StrainFactory.create(active=True)

    @patch('apps.strains.api_views.moderate_strain_comment')
    def test_authenticated_user_can_submit_approved_comment(self, mocked_moderation):
        mocked_moderation.return_value.status = 'approved'
        mocked_moderation.return_value.reason = 'clean'
        self.client.login(email='api-comments@example.com', password='testpass123')

        response = self.client.post(
            reverse('strains_api:comment_submit'),
            data=json.dumps({
                'strain_id': self.strain.id,
                'pros': 'Great for relaxing',
                'cons': 'Bit dry',
                'reaction': 'thumbs_up',
            }),
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload['status'], 'approved')
        self.assertIn('html', payload)
        self.assertTrue(StrainComment.objects.filter(user=self.user, strain=self.strain).exists())

    def test_submit_requires_authentication(self):
        response = self.client.post(
            reverse('strains_api:comment_submit'),
            data=json.dumps({'strain_id': self.strain.id}),
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 403)

    @patch('apps.strains.api_views.moderate_strain_comment')
    def test_submit_updates_existing_comment(self, mocked_moderation):
        mocked_moderation.return_value.status = 'pending'
        mocked_moderation.return_value.reason = 'provider_error'
        StrainComment.objects.create(
            user=self.user,
            strain=self.strain,
            pros='Old',
            cons='Old',
            reaction='thumbs_up',
            status='approved',
        )
        self.client.login(email='api-comments@example.com', password='testpass123')

        response = self.client.post(
            reverse('strains_api:comment_submit'),
            data=json.dumps({
                'strain_id': self.strain.id,
                'pros': 'New pros',
                'cons': 'New cons',
                'reaction': 'thumbs_down',
            }),
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 200)
        comment = StrainComment.objects.get(user=self.user, strain=self.strain)
        self.assertEqual(comment.pros, 'New pros')
        self.assertEqual(comment.status, 'pending')
        self.assertEqual(StrainComment.objects.filter(user=self.user, strain=self.strain).count(), 1)

    def test_submit_validates_payload(self):
        self.client.login(email='api-comments@example.com', password='testpass123')

        response = self.client.post(
            reverse('strains_api:comment_submit'),
            data=json.dumps({
                'strain_id': self.strain.id,
                'pros': '',
                'cons': '',
                'reaction': 'thumbs_up',
            }),
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 400)

    def test_comment_list_returns_approved_comments_only(self):
        StrainComment.objects.create(
            user=self.user,
            strain=self.strain,
            pros='Approved comment',
            cons='Minor downside',
            reaction='thumbs_up',
            status='approved',
        )
        StrainComment.objects.create(
            user=User.objects.create_user(email='hidden@example.com', password='testpass123'),
            strain=self.strain,
            pros='Hidden',
            cons='Hidden',
            reaction='thumbs_down',
            status='pending',
        )

        response = self.client.get(
            reverse('strains_api:comment_list'),
            {'strain_id': self.strain.id, 'page': 1},
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertIn('Approved comment', payload['html'])
        self.assertNotIn('Hidden', payload['html'])

    def test_comment_list_requires_valid_page(self):
        response = self.client.get(
            reverse('strains_api:comment_list'),
            {'strain_id': self.strain.id, 'page': 0},
        )

        self.assertEqual(response.status_code, 400)
