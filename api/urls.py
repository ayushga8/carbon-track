from django.urls import path
from . import views

app_name = 'api'

urlpatterns = [
    path('stats/', views.CarbonStatsAPIView.as_view(), name='stats'),
    path('breakdown/', views.CategoryBreakdownAPIView.as_view(), name='breakdown'),
    path('trends/', views.CarbonTrendsAPIView.as_view(), name='trends'),
    path('leaderboard/', views.LeaderboardAPIView.as_view(), name='leaderboard'),
]
