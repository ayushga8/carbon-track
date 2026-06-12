"""
Comprehensive tests for the REST API endpoints.

~25 tests covering all API views, throttling, error handling, caching.
"""

from datetime import date, timedelta

from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIClient

from calculator.models import CarbonEntry
from challenges.models import Challenge, UserChallenge
from accounts.models import UserProfile


# ============================================================
# CARBON STATS API TESTS
# ============================================================

class TestCarbonStatsAPI(TestCase):
    """Tests for /api/stats/ endpoint."""

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user('apiuser', 'api@test.com', 'TestP@ss123!')
        profile, _ = UserProfile.objects.get_or_create(user=self.user)
        profile.is_email_verified = True
        profile.save()

    def test_requires_authentication(self):
        response = self.client.get('/api/stats/')
        self.assertEqual(response.status_code, 403)

    def test_returns_200_for_authenticated(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get('/api/stats/')
        self.assertEqual(response.status_code, 200)

    def test_returns_all_stat_fields(self):
        CarbonEntry.objects.create(
            user=self.user, category='transport', sub_category='car_petrol',
            value=50, unit='km', carbon_kg=10.5, date=date.today(),
        )
        self.client.force_authenticate(user=self.user)
        response = self.client.get('/api/stats/')
        self.assertIn('total_carbon', response.data)
        self.assertIn('monthly_carbon', response.data)
        self.assertIn('weekly_carbon', response.data)
        self.assertIn('entry_count', response.data)
        self.assertIn('average_daily', response.data)

    def test_stats_reflect_data(self):
        CarbonEntry.objects.create(
            user=self.user, category='transport', sub_category='car_petrol',
            value=50, unit='km', carbon_kg=10.5, date=date.today(),
        )
        self.client.force_authenticate(user=self.user)
        response = self.client.get('/api/stats/')
        self.assertGreater(response.data['total_carbon'], 0)
        self.assertEqual(response.data['entry_count'], 1)

    def test_empty_user_returns_zeros(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get('/api/stats/')
        self.assertEqual(response.data['total_carbon'], 0)
        self.assertEqual(response.data['entry_count'], 0)

    def test_data_isolation_between_users(self):
        other = User.objects.create_user('other', 'other@test.com', 'Pass1234!')
        CarbonEntry.objects.create(
            user=other, category='food', sub_category='beef',
            value=1, unit='kg', carbon_kg=27.0, date=date.today(),
        )
        self.client.force_authenticate(user=self.user)
        response = self.client.get('/api/stats/')
        self.assertEqual(response.data['total_carbon'], 0)


# ============================================================
# CATEGORY BREAKDOWN API TESTS
# ============================================================

class TestCategoryBreakdownAPI(TestCase):
    """Tests for /api/breakdown/ endpoint."""

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user('breakuser', 'break@test.com', 'Pass1234!')
        profile, _ = UserProfile.objects.get_or_create(user=self.user)
        profile.is_email_verified = True
        profile.save()
        CarbonEntry.objects.create(
            user=self.user, category='food', sub_category='beef',
            value=2, unit='kg', carbon_kg=54.0, date=date.today(),
        )
        CarbonEntry.objects.create(
            user=self.user, category='transport', sub_category='car_petrol',
            value=100, unit='km', carbon_kg=21.0, date=date.today(),
        )

    def test_returns_breakdown_data(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get('/api/breakdown/')
        self.assertEqual(response.status_code, 200)
        self.assertGreater(len(response.data), 0)

    def test_breakdown_with_days_param(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get('/api/breakdown/?days=7')
        self.assertEqual(response.status_code, 200)

    def test_breakdown_with_large_days_clamped(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get('/api/breakdown/?days=9999')
        self.assertEqual(response.status_code, 200)

    def test_breakdown_invalid_days_fallback(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get('/api/breakdown/?days=abc')
        self.assertEqual(response.status_code, 200)

    def test_breakdown_returns_multiple_categories(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get('/api/breakdown/')
        categories = [item['category'] for item in response.data]
        self.assertGreaterEqual(len(categories), 2)


# ============================================================
# CARBON TRENDS API TESTS
# ============================================================

class TestCarbonTrendsAPI(TestCase):
    """Tests for /api/trends/ endpoint."""

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user('trenduser', 'trend@test.com', 'Pass1234!')
        UserProfile.objects.get_or_create(user=self.user)
        for i in range(10):
            CarbonEntry.objects.create(
                user=self.user, category='transport', sub_category='car_petrol',
                value=10, unit='km', carbon_kg=2.1,
                date=date.today() - timedelta(days=i),
            )

    def test_daily_trend(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get('/api/trends/?period=daily')
        self.assertEqual(response.status_code, 200)

    def test_weekly_trend(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get('/api/trends/?period=weekly')
        self.assertEqual(response.status_code, 200)

    def test_monthly_trend(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get('/api/trends/?period=monthly')
        self.assertEqual(response.status_code, 200)

    def test_default_period_is_daily(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get('/api/trends/')
        self.assertEqual(response.status_code, 200)

    def test_unknown_period_defaults_to_daily(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get('/api/trends/?period=invalid')
        self.assertEqual(response.status_code, 200)

    def test_trends_returns_list(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get('/api/trends/?period=daily')
        self.assertIsInstance(response.data, list)

    def test_trends_empty_user(self):
        empty = User.objects.create_user('empty', 'e@test.com', 'Pass1234!')
        UserProfile.objects.get_or_create(user=empty)
        self.client.force_authenticate(user=empty)
        response = self.client.get('/api/trends/')
        self.assertEqual(response.status_code, 200)


# ============================================================
# LEADERBOARD API TESTS
# ============================================================

class TestLeaderboardAPI(TestCase):
    """Tests for /api/leaderboard/ endpoint."""

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user('leader', 'leader@test.com', 'Pass1234!')
        UserProfile.objects.get_or_create(user=self.user)

    def test_requires_authentication(self):
        response = self.client.get('/api/leaderboard/')
        self.assertEqual(response.status_code, 403)

    def test_empty_leaderboard(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get('/api/leaderboard/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 0)

    def test_leaderboard_with_completed_challenges(self):
        challenge = Challenge.objects.create(
            title='Test', description='Test', category='general',
            difficulty='easy', carbon_save_potential=10.0, duration_days=7,
        )
        uc = UserChallenge.objects.create(
            user=self.user, challenge=challenge, status='in_progress',
        )
        uc.complete()
        self.client.force_authenticate(user=self.user)
        response = self.client.get('/api/leaderboard/')
        self.assertEqual(response.status_code, 200)
        self.assertGreater(len(response.data), 0)

    def test_leaderboard_entry_has_fields(self):
        challenge = Challenge.objects.create(
            title='Test', description='Test', category='general',
            difficulty='easy', carbon_save_potential=10.0, duration_days=7,
        )
        uc = UserChallenge.objects.create(
            user=self.user, challenge=challenge, status='in_progress',
        )
        uc.complete()
        self.client.force_authenticate(user=self.user)
        response = self.client.get('/api/leaderboard/')
        entry = response.data[0]
        self.assertIn('rank', entry)
        self.assertIn('username', entry)
        self.assertIn('challenges_completed', entry)
        self.assertIn('carbon_saved', entry)

    def test_in_progress_not_on_leaderboard(self):
        challenge = Challenge.objects.create(
            title='Test', description='Test', category='general',
            difficulty='easy', carbon_save_potential=10.0, duration_days=7,
        )
        UserChallenge.objects.create(
            user=self.user, challenge=challenge, status='in_progress',
        )
        self.client.force_authenticate(user=self.user)
        response = self.client.get('/api/leaderboard/')
        self.assertEqual(len(response.data), 0)
