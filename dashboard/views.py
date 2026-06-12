"""
Dashboard views for data visualization and insights.
"""
import json
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView

from .services import StatsService, InsightsService


class DashboardView(LoginRequiredMixin, TemplateView):
    """Main dashboard with stats, charts, and personalized insights."""
    template_name = 'dashboard/dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user

        # Carbon stats
        context['total_carbon'] = StatsService.get_total_carbon(user)
        context['monthly_carbon'] = StatsService.get_total_carbon(user, days=30)
        context['weekly_carbon'] = StatsService.get_total_carbon(user, days=7)
        context['entry_count'] = StatsService.get_entry_count(user)
        context['average_daily'] = StatsService.get_average_daily(user, days=30)

        # Chart data (serialize for JavaScript)
        category_breakdown = StatsService.get_category_breakdown(user, days=30)
        context['category_data_json'] = json.dumps(category_breakdown)

        daily_trend = StatsService.get_daily_trend(user, days=30)
        # Convert dates to strings for JSON
        for item in daily_trend:
            if item.get('day'):
                item['day'] = item['day'].strftime('%Y-%m-%d')
        context['trend_data_json'] = json.dumps(daily_trend)

        # Comparison data
        comparison = InsightsService.get_comparison(user)
        context['comparison_data_json'] = json.dumps(comparison)
        context['comparison'] = comparison

        # Personalized insights
        context['insights'] = InsightsService.get_insights(user)

        return context
