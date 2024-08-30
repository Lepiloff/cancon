from django.urls import path
from apps.strains import views

urlpatterns = [
    path('', views.main_page, name='main_page'),
    path('strains/', views.strain_list, name='strain_list'),
    path('strain/<slug:slug>/', views.strain_detail, name='strain_detail'),
    path('search/', views.search, name='search'),
    path('articles/', views.article_list, name='article_list'),
    path('articles/<slug:slug>/', views.article_detail, name='article_detail'),
    path('terpenes/', views.terpene_list, name='terpene_list'),
    path('terpenes/<slug:slug>/', views.terpene_detail, name='terpene_detail'),
]