from django.urls import path

from . import views


urlpatterns = [
    path('dashboard/', views.dashboard, name='dashboard'),
    path('dashboard/favorites/', views.dashboard_favorites, name='dashboard_favorites'),
    path('dashboard/comments/', views.dashboard_comments, name='dashboard_comments'),
    path('dashboard/journal/', views.dashboard_journal, name='dashboard_journal'),
    path('dashboard/settings/', views.dashboard_settings, name='dashboard_settings'),
    path('dashboard/journal/create/', views.journal_create, name='journal_create'),
    path('dashboard/journal/<int:note_id>/update/', views.journal_update, name='journal_update'),
    path('dashboard/journal/<int:note_id>/delete/', views.journal_delete, name='journal_delete'),
    path('dashboard/journal/<int:note_id>/json/', views.journal_note_json, name='journal_json'),
]
