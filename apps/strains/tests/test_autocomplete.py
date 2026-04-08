from django.test import Client, TestCase
from django.urls import reverse
from django.utils.translation import override

from apps.strains.factories import StrainFactory


class StrainAutocompleteApiTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.active_strain = StrainFactory.create(active=True, name='Blue Dream')
        self.inactive_strain = StrainFactory.create(active=False, name='Hidden Dream')

    def test_returns_matching_active_strains(self):
        response = self.client.get(reverse('strains_api:strain_autocomplete'), {'q': 'Dream'})

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        names = [item['name'] for item in payload['results']]
        self.assertIn(self.active_strain.name, names)
        self.assertNotIn(self.inactive_strain.name, names)

    def test_returns_empty_results_for_blank_query(self):
        response = self.client.get(reverse('strains_api:strain_autocomplete'), {'q': ''})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['results'], [])

    def test_reverse_remains_non_localized_under_en_language(self):
        with override('en'):
            url = reverse('strains_api:strain_autocomplete')

        self.assertEqual(url, '/api/strains/autocomplete/')
