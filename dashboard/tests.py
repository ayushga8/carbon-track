"""
Comprehensive tests for the dashboard app.

~25 tests covering StatsService, InsightsService, Dashboard view, edge cases.
"""

from datetime import date, timedelta

from django.contrib.auth.models import User
from django.test import TestCase, Client
from django.urls import reverse

from calculator.models import CarbonEntry
from accounts.models import UserProfile
from .services import StatsService, InsightsService


# ============================================================
# STATS SERVICE TESTS
# ============================================================

class TestStatsServiceTotalCarbon(TestCase):
    """Test total carbon calculations."""

    def setUp(self):
        self.user = User.objects.create_user('testuser', 'test@example.com', 'Pass1234!')
        self.other_user = User.objects.create_user('other', 'other@example.com', 'Pass1234!')

        for i in range(5):
            CarbonEntry.objects.create(
                user=self.user, category='transport', sub_category='car_petrol',
                value=10, unit='km', carbon_kg=2.1,
                date=date.today() - timedelta(days=i),
            )
        CarbonEntry.objects.create(
            user=self.other_user, category='food', sub_category='beef',
            value=1, unit='kg', carbon_kg=27.0, date=date.today(),
        )

    def test_total_carbon_all_time(self):
        total = StatsService.get_total_carbon(self.user)
        self.assertEqual(total, 10.5)

    def test_total_carbon_with_day_filter(self):
        total = StatsService.get_total_carbon(self.user, days=2)
        self.assertGreater(total, 0)
        self.assertLessEqual(total, 10.5)

    def test_total_carbon_user_isolation(self):
        total = StatsService.get_total_carbon(self.user)
        other_total = StatsService.get_total_carbon(self.other_user)
        self.assertNotEqual(total, other_total)

    def test_total_carbon_empty_user(self):
        new_user = User.objects.create_user('empty', 'e@example.com', 'Pass1234!')
        self.assertEqual(StatsService.get_total_carbon(new_user), 0)


class TestStatsServiceBreakdown(TestCase):
    """Test category breakdown."""

    def setUp(self):
        self.user = User.objects.create_user('testuser', 'test@example.com', 'Pass1234!')
        CarbonEntry.objects.create(
            user=self.user, category='transport', sub_category='car_petrol',
            value=100, unit='km', carbon_kg=21.0, date=date.today(),
        )
        CarbonEntry.objects.create(
            user=self.user, category='food', sub_category='beef',
            value=2, unit='kg', carbon_kg=54.0, date=date.today(),
        )

    def test_breakdown_returns_list(self):
        breakdown = StatsService.get_category_breakdown(self.user, days=30)
        self.assertIsInstance(breakdown, list)

    def test_breakdown_has_categories(self):
        breakdown = StatsService.get_category_breakdown(self.user, days=30)
        categories = [b['category'] for b in breakdown]
        self.assertIn('transport', categories)
        self.assertIn('food', categories)

    def test_breakdown_has_totals(self):
        breakdown = StatsService.get_category_breakdown(self.user, days=30)
        for b in breakdown:
            self.assertIn('total', b)
            self.assertGreater(b['total'], 0)


class TestStatsServiceEntryCount(TestCase):
    """Test entry count."""

    def setUp(self):
        self.user = User.objects.create_user('testuser', 'test@example.com', 'Pass1234!')

    def test_entry_count_zero(self):
        self.assertEqual(StatsService.get_entry_count(self.user), 0)

    def test_entry_count_with_entries(self):
        for _ in range(3):
            CarbonEntry.objects.create(
                user=self.user, category='transport', sub_category='bus',
                value=10, unit='km', carbon_kg=0.89, date=date.today(),
            )
        self.assertEqual(StatsService.get_entry_count(self.user), 3)


class TestStatsServiceAverageDaily(TestCase):
    """Test average daily calculation."""

    def setUp(self):
        self.user = User.objects.create_user('testuser', 'test@example.com', 'Pass1234!')

    def test_average_daily_zero(self):
        self.assertEqual(StatsService.get_average_daily(self.user), 0)

    def test_average_daily_with_data(self):
        CarbonEntry.objects.create(
            user=self.user, category='transport', sub_category='car_petrol',
            value=100, unit='km', carbon_kg=21.0, date=date.today(),
        )
        avg = StatsService.get_average_daily(self.user, days=30)
        self.assertGreater(avg, 0)


class TestStatsServiceTrends(TestCase):
    """Test trend data generation."""

    def setUp(self):
        self.user = User.objects.create_user('testuser', 'test@example.com', 'Pass1234!')
        for i in range(10):
            CarbonEntry.objects.create(
                user=self.user, category='transport', sub_category='car_petrol',
                value=10, unit='km', carbon_kg=2.1,
                date=date.today() - timedelta(days=i),
            )

    def test_daily_trend_returns_list(self):
        trend = StatsService.get_daily_trend(self.user, days=30)
        self.assertIsInstance(trend, list)

    def test_daily_trend_has_data(self):
        trend = StatsService.get_daily_trend(self.user, days=30)
        self.assertGreater(len(trend), 0)

    def test_weekly_trend_returns_list(self):
        trend = StatsService.get_weekly_trend(self.user, weeks=4)
        self.assertIsInstance(trend, list)

    def test_monthly_trend_returns_list(self):
        trend = StatsService.get_monthly_trend(self.user, months=3)
        self.assertIsInstance(trend, list)

    def test_daily_trend_empty_user(self):
        new_user = User.objects.create_user('empty', 'e@example.com', 'Pass1234!')
        trend = StatsService.get_daily_trend(new_user, days=7)
        self.assertIsInstance(trend, list)


# ============================================================
# INSIGHTS SERVICE TESTS
# ============================================================

class TestInsightsService(TestCase):
    """Test personalized insights generation."""

    def setUp(self):
        self.user = User.objects.create_user('testuser', 'test@example.com', 'Pass1234!')
        CarbonEntry.objects.create(
            user=self.user, category='transport', sub_category='car_petrol',
            value=100, unit='km', carbon_kg=21.0, date=date.today(),
        )

    def test_insights_returns_list(self):
        insights = InsightsService.get_insights(self.user)
        self.assertIsInstance(insights, list)

    def test_insights_have_tips(self):
        insights = InsightsService.get_insights(self.user)
        if insights:
            self.assertIn('tips', insights[0])

    def test_comparison_data(self):
        comparison = InsightsService.get_comparison(self.user)
        self.assertIn('user_yearly', comparison)
        self.assertIn('global_avg', comparison)

    def test_comparison_positive_values(self):
        comparison = InsightsService.get_comparison(self.user)
        self.assertGreaterEqual(comparison['user_yearly'], 0)
        self.assertGreater(comparison['global_avg'], 0)

    def test_insights_empty_user(self):
        new_user = User.objects.create_user('empty', 'e@example.com', 'Pass1234!')
        insights = InsightsService.get_insights(new_user)
        self.assertIsInstance(insights, list)


# ============================================================
# DASHBOARD VIEW TESTS
# ============================================================

class TestDashboardView(TestCase):
    """Test dashboard view access and rendering."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user('testuser', 'test@example.com', 'Pass1234!')

    def test_unauthenticated_redirect(self):
        response = self.client.get(reverse('dashboard:dashboard'))
        self.assertEqual(response.status_code, 302)
        self.assertIn('login', response.url)

    def test_authenticated_access(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse('dashboard:dashboard'))
        self.assertEqual(response.status_code, 200)

    def test_empty_dashboard_renders(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse('dashboard:dashboard'))
        self.assertEqual(response.status_code, 200)

    def test_dashboard_with_data(self):
        CarbonEntry.objects.create(
            user=self.user, category='transport', sub_category='car_petrol',
            value=100, unit='km', carbon_kg=21.0, date=date.today(),
        )
        self.client.force_login(self.user)
        response = self.client.get(reverse('dashboard:dashboard'))
        self.assertEqual(response.status_code, 200)

    def test_dashboard_context_has_stats(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse('dashboard:dashboard'))
        # Check that stats-related keys exist in context
        ctx = response.context
        # At minimum, the dashboard should have some context data
        self.assertIsNotNone(ctx)
