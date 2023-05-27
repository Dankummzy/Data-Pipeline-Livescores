from django.urls import path

from .views import livescores, get_matches, team_analysis, about_us, privacy_policy

urlpatterns = [
    path('', get_matches, name='matches'),
    path('livescores', livescores, name='livescores'),
    path('analysis/<int:match_id>/', team_analysis, name='team_analysis'),
    path('about/', about_us, name='about_us'),
    path('privacy/', privacy_policy, name='privacy_policy'),
]
