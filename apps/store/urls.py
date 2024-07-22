from django.urls import path
from apps.store import views

urlpatterns = [
    path('map/', views.map_view, name='map_view'),
]