from django.urls import path

from apps.strains import api_views


app_name = 'strains_api'

urlpatterns = [
    path('favorites/toggle/', api_views.favorite_toggle, name='favorite_toggle'),
    path('favorites/status/', api_views.favorite_status, name='favorite_status'),
    path('comments/submit/', api_views.comment_submit, name='comment_submit'),
    path('comments/list/', api_views.comment_list, name='comment_list'),
]
