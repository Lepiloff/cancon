from django.urls import path
from . import views

app_name = 'chat_bot'

urlpatterns = [
    path('config/', views.ChatConfigView.as_view(), name='config'),
    path('chat/', views.ChatProxyView.as_view(), name='chat'),
    path('feedback/', views.ChatFeedbackView.as_view(), name='feedback'),
    path('health/', views.chat_health, name='health'),
    path('stats/', views.chat_stats, name='stats'),
]