from django.urls import reverse, resolve
from apps.strains import views


def test_main_page_url():
    url = reverse('main_page')
    assert url == '/'
    assert resolve(url).func == views.main_page


def test_strain_list_url():
    url = reverse('strain_list')
    assert url == '/strains/'
    assert resolve(url).func == views.strain_list


def test_strain_detail_url():
    url = reverse('strain_detail', kwargs={'slug': 'test-slug'})
    assert url == '/strain/test-slug/'
    assert resolve(url).func == views.strain_detail


def test_search_url():
    url = reverse('search')
    assert url == '/search/'
    assert resolve(url).func == views.search


def test_article_list_url():
    url = reverse('article_list')
    assert url == '/articles/'
    assert resolve(url).func == views.article_list


def test_article_detail_url():
    url = reverse('article_detail', kwargs={'slug': 'test-slug'})
    assert url == '/articles/test-slug/'
    assert resolve(url).func == views.article_detail
