from django.urls import path

from .views import get_matches, team_analysis, about_us, privacy_policy

urlpatterns = [
    path('', get_matches, name='matches'),
    path('team-analysis/<int:event_id>/', team_analysis, name='team_analysis'),
    path('about/', about_us, name='about_us'),
    path('privacy/', privacy_policy, name='privacy_policy'),
]
