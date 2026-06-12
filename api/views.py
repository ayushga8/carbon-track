"""
REST API views for the Carbon Footprint Platform.

Security:
- All endpoints require authentication
- Error handling on query params
- Efficient annotated queries (no N+1 loops)
- Cached leaderboard
"""

from django.contrib.auth.models import User
from django.db.models import Count, Sum, Q

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.throttling import UserRateThrottle

from django.core.cache import cache
from dashboard.services import StatsService
from .serializers import (
    CarbonStatsSerializer,
    CategoryBreakdownSerializer,
    TrendDataSerializer,
    LeaderboardEntrySerializer,
)


class StandardThrottle(UserRateThrottle):
    """100 requests per hour per user."""
    rate = '100/hour'


class CarbonStatsAPIView(APIView):
    """GET: Returns user's aggregated carbon statistics."""
    permission_classes = [IsAuthenticated]
    throttle_classes = [StandardThrottle]

    def get(self, request):
        user = request.user
        data = {
            'total_carbon': StatsService.get_total_carbon(user),
            'monthly_carbon': StatsService.get_total_carbon(user, days=30),
            'weekly_carbon': StatsService.get_total_carbon(user, days=7),
            'entry_count': StatsService.get_entry_count(user),
            'average_daily': StatsService.get_average_daily(user, days=30),
        }
        serializer = CarbonStatsSerializer(data)
        return Response(serializer.data)


class CategoryBreakdownAPIView(APIView):
    """GET: Returns emissions breakdown by category."""
    permission_classes = [IsAuthenticated]
    throttle_classes = [StandardThrottle]

    def get(self, request):
        user = request.user
        try:
            days = int(request.query_params.get('days', 30))
        except (ValueError, TypeError):
            days = 30
        days = min(max(days, 1), 365)  # Clamp between 1 and 365

        breakdown = StatsService.get_category_breakdown(user, days=days)
        serializer = CategoryBreakdownSerializer(breakdown, many=True)
        return Response(serializer.data)


class CarbonTrendsAPIView(APIView):
    """GET: Returns time-series trend data."""
    permission_classes = [IsAuthenticated]
    throttle_classes = [StandardThrottle]

    def get(self, request):
        user = request.user
        period = request.query_params.get('period', 'daily')

        if period == 'weekly':
            data = StatsService.get_weekly_trend(user, weeks=12)
        elif period == 'monthly':
            data = StatsService.get_monthly_trend(user, months=12)
        else:
            data = StatsService.get_daily_trend(user, days=30)

        # Serialize dates and use TrendDataSerializer
        result = []
        for item in data:
            date_val = item.get('day') or item.get('week') or item.get('month')
            result.append({
                'date': date_val.strftime('%Y-%m-%d') if date_val else None,
                'total': round(item.get('total', 0), 2),
            })

        serializer = TrendDataSerializer(result, many=True)
        return Response(serializer.data)


class LeaderboardAPIView(APIView):
    """
    GET: Returns top 20 users by challenges completed.

    Uses efficient annotated query instead of N+1 loop.
    Cached for 5 minutes.
    """
    permission_classes = [IsAuthenticated]
    throttle_classes = [StandardThrottle]

    def get(self, request):
        cache_key = 'api_leaderboard_top20'
        cached = cache.get(cache_key)
        if cached:
            return Response(cached)

        # Single efficient query with annotations — no N+1
        users = (
            User.objects.annotate(
                challenges_completed=Count(
                    'user_challenges',
                    filter=Q(user_challenges__status='completed'),
                ),
                carbon_saved=Sum(
                    'user_challenges__challenge__carbon_save_potential',
                    filter=Q(user_challenges__status='completed'),
                ),
            )
            .filter(challenges_completed__gt=0)
            .order_by('-challenges_completed', '-carbon_saved')
            .values('username', 'challenges_completed', 'carbon_saved')[:20]
        )

        result = []
        for rank, entry in enumerate(users, 1):
            result.append({
                'rank': rank,
                'username': entry['username'],
                'challenges_completed': entry['challenges_completed'],
                'carbon_saved': float(entry['carbon_saved'] or 0),
            })

        serializer = LeaderboardEntrySerializer(result, many=True)
        cache.set(cache_key, serializer.data, 300)
        return Response(serializer.data)
