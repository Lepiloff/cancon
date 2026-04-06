from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from apps.strains.factories import StrainFactory
from apps.strains.models import FavoriteStrain


User = get_user_model()


class FavoriteApiTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            email='favorites@example.com',
            password='testpass123',
        )
        self.strain = StrainFactory.create(active=True)

    def test_toggle_requires_login(self):
        response = self.client.post(
            reverse('strains_api:favorite_toggle'),
            data='{"strain_id": %s}' % self.strain.id,
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 403)

    def test_status_requires_login(self):
        response = self.client.get(
            reverse('strains_api:favorite_status'),
            {'strain_ids': str(self.strain.id)},
        )

        self.assertEqual(response.status_code, 403)

    def test_toggle_adds_favorite(self):
        self.client.login(email='favorites@example.com', password='testpass123')

        response = self.client.post(
            reverse('strains_api:favorite_toggle'),
            data='{"strain_id": %s}' % self.strain.id,
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['status'], 'added')
        self.assertTrue(FavoriteStrain.objects.filter(user=self.user, strain=self.strain).exists())

    def test_toggle_removes_favorite(self):
        FavoriteStrain.objects.create(user=self.user, strain=self.strain)
        self.client.login(email='favorites@example.com', password='testpass123')

        response = self.client.post(
            reverse('strains_api:favorite_toggle'),
            data='{"strain_id": %s}' % self.strain.id,
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['status'], 'removed')
        self.assertFalse(FavoriteStrain.objects.filter(user=self.user, strain=self.strain).exists())

    def test_status_returns_favorited_ids(self):
        other_strain = StrainFactory.create(active=True)
        FavoriteStrain.objects.create(user=self.user, strain=self.strain)
        self.client.login(email='favorites@example.com', password='testpass123')

        response = self.client.get(
            reverse('strains_api:favorite_status'),
            {'strain_ids': f'{self.strain.id},{other_strain.id}'},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['favorites'], [self.strain.id])

    def test_toggle_rejects_unknown_strain(self):
        self.client.login(email='favorites@example.com', password='testpass123')

        response = self.client.post(
            reverse('strains_api:favorite_toggle'),
            data='{"strain_id": 999999}',
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 404)

    def test_toggle_rejects_invalid_json(self):
        self.client.login(email='favorites@example.com', password='testpass123')

        response = self.client.post(
            reverse('strains_api:favorite_toggle'),
            data='{"strain_id":',
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 400)

    def test_status_rejects_invalid_ids(self):
        self.client.login(email='favorites@example.com', password='testpass123')

        response = self.client.get(
            reverse('strains_api:favorite_status'),
            {'strain_ids': 'abc,123'},
        )

        self.assertEqual(response.status_code, 400)


class FavoriteViewIntegrationTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            email='detail@example.com',
            password='testpass123',
        )
        self.strain = StrainFactory.create(active=True)

    def test_strain_detail_marks_favorite_for_authenticated_user(self):
        FavoriteStrain.objects.create(user=self.user, strain=self.strain)
        self.client.login(email='detail@example.com', password='testpass123')

        response = self.client.get(reverse('strain_detail', args=[self.strain.slug]))

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['is_favorited'])

    def test_strain_detail_defaults_to_not_favorited_for_anonymous_user(self):
        response = self.client.get(reverse('strain_detail', args=[self.strain.slug]))

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context['is_favorited'])
