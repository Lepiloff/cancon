from unittest.mock import patch
from django.test import TestCase, Client
from django.urls import reverse

from apps.strains.factories import (
    StrainFactory, ArticleFactory, ArticleCategoryFactory, AlternativeNameFactory
)


class ViewsTestCase(TestCase):

    def setUp(self):
        self.client = Client()

    def test_main_page_view(self):
        StrainFactory.create_batch(8, active=True, main=True)
        ArticleFactory.create_batch(6)

        response = self.client.get(reverse('main_page'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'main.html')

    def test_strain_detail_view_exists(self):
        strain = StrainFactory.create()

        response = self.client.get(reverse('strain_detail', args=[strain.slug]))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'strain.html')

    def test_strain_detail_view_not_exists(self):
        response = self.client.get(reverse('strain_detail', args=['non-existent-slug']))
        self.assertEqual(response.status_code, 404)

    def test_strain_list_view(self):
        StrainFactory.create_batch(5, active=True)

        response = self.client.get(reverse('strain_list'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'strains.html')

    def test_strain_list_view_with_filters(self):
        strain1 = StrainFactory.create(name="Strain A", category="Indica")
        strain2 = StrainFactory.create(name="Strain B", category="Sativa")
        strain3 = StrainFactory.create(name="Strain C", category="Hybrid")

        response = self.client.get(reverse('strain_list'), {'category': 'Indica'})

        self.assertContains(response, strain1.name)
        self.assertNotContains(response, strain2.name)
        self.assertNotContains(response, strain3.name)

    def test_article_detail_view_exists(self):
        article = ArticleFactory.create()

        response = self.client.get(reverse('article_detail', args=[article.slug]))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'article_detail.html')

    def test_article_detail_view_not_exists(self):
        response = self.client.get(reverse('article_detail', args=['non-existent-slug']))
        self.assertEqual(response.status_code, 404)

    def test_article_list_view(self):
        ArticleFactory.create_batch(5)

        response = self.client.get(reverse('article_list'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'articles.html')

    def test_article_list_view_with_category(self):
        category1 = ArticleCategoryFactory(name="Category A")
        category2 = ArticleCategoryFactory(name="Category B")

        article1 = ArticleFactory(category=[category1])
        article2 = ArticleFactory(category=[category1])
        article3 = ArticleFactory(category=[category2])

        response = self.client.get(reverse('article_list'), {'category': 'Category A'})

        self.assertContains(response, article1.title)
        self.assertContains(response, article2.title)
        self.assertNotContains(response, article3.title)

    @patch('apps.strains.views.is_ajax_request', return_value=True)
    def test_search_view_with_ajax_query(self, _mocked_is_ajax):
        strain = StrainFactory.create(name="Test Strain")

        response = self.client.get(reverse('search'), {'q': 'Test'},
                                   HTTP_X_REQUESTED_WITH='XMLHttpRequest')

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, strain.name)

    def test_search_view_with_ajax_query_alternative_name(self):
        strain = StrainFactory()
        AlternativeNameFactory(strain=strain, name="Alternative Strain Name")
        response = self.client.get(reverse('search'), {'q': 'Alternative'},
                                   HTTP_X_REQUESTED_WITH='XMLHttpRequest')

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, strain.name)

    def test_search_view_with_query(self):
        strain = StrainFactory.create(name="Test Strain")

        response = self.client.get(reverse('search'), {'q': 'Test'})
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith(reverse('main_page')))

    def test_search_view_without_query(self):
        response = self.client.get(reverse('search'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "No query provided")

    def test_search_view_no_results(self):
        StrainFactory.create(name="Blue Dream")
        StrainFactory.create(name="Sour Diesel")
        StrainFactory.create(name="Girl Scout Cookies")

        response = self.client.get(reverse('search'), {'q': 'Nonexistent Strain'}, HTTP_X_REQUESTED_WITH='XMLHttpRequest')

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "Blue Dream")
        self.assertNotContains(response, "Sour Diesel")
        self.assertNotContains(response, "Girl Scout Cookies")

