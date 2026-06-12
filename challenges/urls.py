"""URL configuration for the Challenges application."""

from django.urls import path

from . import views

app_name = 'challenges'

urlpatterns = [
    path('', views.ChallengeListView.as_view(), name='challenge_list'),
    path('<int:pk>/', views.ChallengeDetailView.as_view(), name='challenge_detail'),
    path('<int:pk>/join/', views.JoinChallengeView.as_view(), name='join_challenge'),
    path('<int:pk>/progress/', views.UpdateProgressView.as_view(), name='update_progress'),
    path('leaderboard/', views.LeaderboardView.as_view(), name='leaderboard'),
]
