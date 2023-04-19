from django.urls import path
from . import views

urlpatterns = [
    path('strains/', views.strain_list, name='strain_list'),
    path('strain/<slug:slug>/', views.strain_detail, name='strain_detail'),
]