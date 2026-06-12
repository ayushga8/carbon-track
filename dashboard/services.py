"""
Dashboard services for stats aggregation and personalized insights.
"""
from datetime import timedelta
import random

from django.db.models import Sum, Avg, Count
from django.db.models.functions import TruncDay, TruncWeek, TruncMonth
from django.utils import timezone

from calculator.models import CarbonEntry


class StatsService:
    """Aggregates carbon data for dashboard visualization."""

    @staticmethod
    def get_total_carbon(user, days=None):
        """Get total carbon emissions, optionally filtered by days."""
        qs = CarbonEntry.objects.filter(user=user)
        if days:
            qs = qs.filter(date__gte=timezone.now().date() - timedelta(days=days))
        result = qs.aggregate(total=Sum('carbon_kg'))
        return round(result['total'] or 0, 2)

    @staticmethod
    def get_category_breakdown(user, days=30):
        """Get emissions breakdown by category."""
        qs = CarbonEntry.objects.filter(
            user=user,
            date__gte=timezone.now().date() - timedelta(days=days),
        )
        return list(qs.values('category').annotate(
            total=Sum('carbon_kg'),
            count=Count('id'),
        ).order_by('-total'))

    @staticmethod
    def get_daily_trend(user, days=30):
        """Get daily emission trend data."""
        qs = CarbonEntry.objects.filter(
            user=user,
            date__gte=timezone.now().date() - timedelta(days=days),
        )
        return list(qs.annotate(
            day=TruncDay('date')
        ).values('day').annotate(
            total=Sum('carbon_kg'),
        ).order_by('day'))

    @staticmethod
    def get_weekly_trend(user, weeks=12):
        """Get weekly emission trend data."""
        qs = CarbonEntry.objects.filter(
            user=user,
            date__gte=timezone.now().date() - timedelta(weeks=weeks),
        )
        return list(qs.annotate(
            week=TruncWeek('date')
        ).values('week').annotate(
            total=Sum('carbon_kg'),
        ).order_by('week'))

    @staticmethod
    def get_monthly_trend(user, months=12):
        """Get monthly emission trend data."""
        qs = CarbonEntry.objects.filter(
            user=user,
            date__gte=timezone.now().date() - timedelta(days=months * 30),
        )
        return list(qs.annotate(
            month=TruncMonth('date')
        ).values('month').annotate(
            total=Sum('carbon_kg'),
        ).order_by('month'))

    @staticmethod
    def get_entry_count(user):
        """Get total number of carbon entries for user."""
        return CarbonEntry.objects.filter(user=user).count()

    @staticmethod
    def get_average_daily(user, days=30):
        """Get average daily carbon emission."""
        qs = CarbonEntry.objects.filter(
            user=user,
            date__gte=timezone.now().date() - timedelta(days=days),
        )
        result = qs.aggregate(avg=Avg('carbon_kg'))
        return round(result['avg'] or 0, 2)


class InsightsService:
    """Generates personalized reduction tips based on user data."""

    TIPS = {
        'transport': [
            'Consider carpooling or using public transport to reduce commute emissions.',
            'For short trips under 5km, try cycling or walking.',
            'If possible, switch to an electric vehicle for daily commute.',
            'Plan your trips efficiently to reduce unnecessary driving.',
            'Consider video calls instead of travel for meetings.',
        ],
        'energy': [
            'Switch to LED bulbs — they use 75% less energy.',
            'Unplug devices when not in use to reduce phantom loads.',
            'Set your thermostat 2°C lower in winter, 2°C higher in summer.',
            'Consider installing solar panels for clean energy.',
            'Use a smart power strip to manage standby power.',
        ],
        'food': [
            'Try having one meatless day per week to reduce food emissions.',
            'Choose local and seasonal produce when possible.',
            'Reduce beef consumption — it has the highest carbon footprint.',
            'Try plant-based protein alternatives for some meals.',
            'Buy in bulk to reduce packaging waste.',
        ],
        'shopping': [
            'Buy second-hand or refurbished electronics when possible.',
            'Choose quality items that last longer over fast fashion.',
            'Bring reusable bags when shopping.',
            'Consolidate online orders to reduce delivery trips.',
            'Repair items instead of replacing them.',
        ],
        'waste': [
            'Start composting food scraps — it reduces methane emissions.',
            'Recycle paper, plastic, glass, and metal properly.',
            'Reduce food waste by planning meals ahead.',
            'Use reusable containers instead of disposable ones.',
            'Donate usable items instead of throwing them away.',
        ],
    }

    GLOBAL_AVERAGE = 4700
    INDIA_AVERAGE = 1900
    US_AVERAGE = 15200
    EU_AVERAGE = 6800

    @classmethod
    def get_insights(cls, user):
        """Get personalized tips based on user's highest emission categories."""
        breakdown = StatsService.get_category_breakdown(user, days=30)
        insights = []
        for item in breakdown[:3]:
            category = item['category']
            tips = cls.TIPS.get(category, [])
            if tips:
                selected_tips = random.sample(tips, min(2, len(tips)))
                insights.append({
                    'category': category,
                    'category_display': dict(CarbonEntry.CATEGORY_CHOICES).get(category, category),
                    'total': round(item['total'], 2),
                    'tips': selected_tips,
                })
        return insights

    @classmethod
    def get_comparison(cls, user):
        """Compare user's footprint with global averages."""
        yearly = StatsService.get_total_carbon(user, days=365)
        return {
            'user_yearly': round(yearly, 2),
            'global_avg': cls.GLOBAL_AVERAGE,
            'india_avg': cls.INDIA_AVERAGE,
            'us_avg': cls.US_AVERAGE,
            'eu_avg': cls.EU_AVERAGE,
        }
