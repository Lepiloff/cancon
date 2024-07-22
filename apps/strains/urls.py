from django.urls import path
from apps.strains import views

urlpatterns = [
    path('', views.main_page, name='main_page'),
    path('strains/', views.strain_list, name='strain_list'),
    path('strain/<slug:slug>/', views.strain_detail, name='strain_detail'),
    path('search/', views.search, name='search'),
    path('articles/', views.article_list, name='article_list'),
]
