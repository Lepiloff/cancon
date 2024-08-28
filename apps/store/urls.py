from django.urls import path
from apps.store import views

urlpatterns = [
    path('map/', views.global_map_redirect, name='global_map_redirect'),  # global map
    path('<str:country>/map/', views.map_view, name='map_view'),  # country map
]
