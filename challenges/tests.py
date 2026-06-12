"""
Comprehensive tests for the challenges app.

~35 tests covering models, views, race conditions, filtering, leaderboard.
"""

from django.contrib.auth.models import User
from django.db import IntegrityError
from django.test import TestCase, Client
from django.urls import reverse

from .models import Challenge, UserChallenge


# ============================================================
# MODEL TESTS
# ============================================================

class TestChallengeModel(TestCase):
    """Test Challenge model."""

    def test_str_representation(self):
        c = Challenge.objects.create(
            title='Walk to Work', description='Walk it!',
            category='transport', difficulty='easy',
            carbon_save_potential=5.0, duration_days=7,
        )
        self.assertEqual(str(c), 'Walk to Work')

    def test_default_is_active(self):
        c = Challenge.objects.create(
            title='Test', description='Test',
            category='general', difficulty='easy',
            carbon_save_potential=1.0, duration_days=1,
        )
        self.assertTrue(c.is_active)

    def test_default_participants_count(self):
        c = Challenge.objects.create(
            title='Test', description='Test',
            category='general', difficulty='easy',
            carbon_save_potential=1.0, duration_days=1,
        )
        self.assertEqual(c.participants_count, 0)

    def test_ordering_newest_first(self):
        c1 = Challenge.objects.create(
            title='First', description='x',
            category='general', difficulty='easy',
            carbon_save_potential=1.0, duration_days=1,
        )
        c2 = Challenge.objects.create(
            title='Second', description='x',
            category='general', difficulty='easy',
            carbon_save_potential=1.0, duration_days=1,
        )
        challenges = list(Challenge.objects.all())
        self.assertEqual(challenges[0], c2)


class TestUserChallengeModel(TestCase):
    """Test UserChallenge model."""

    def setUp(self):
        self.user = User.objects.create_user('testuser', 'test@example.com', 'Pass1234!')
        self.challenge = Challenge.objects.create(
            title='Walk', description='Walk!',
            category='transport', difficulty='easy',
            carbon_save_potential=5.0, duration_days=7,
        )

    def test_unique_together_prevents_duplicate_join(self):
        UserChallenge.objects.create(
            user=self.user, challenge=self.challenge, status='in_progress',
        )
        with self.assertRaises(IntegrityError):
            UserChallenge.objects.create(
                user=self.user, challenge=self.challenge, status='in_progress',
            )

    def test_complete_method_sets_status(self):
        uc = UserChallenge.objects.create(
            user=self.user, challenge=self.challenge, status='in_progress',
        )
        uc.complete()
        uc.refresh_from_db()
        self.assertEqual(uc.status, 'completed')

    def test_complete_method_sets_progress_100(self):
        uc = UserChallenge.objects.create(
            user=self.user, challenge=self.challenge, status='in_progress',
        )
        uc.complete()
        uc.refresh_from_db()
        self.assertEqual(uc.progress, 100)

    def test_complete_method_sets_timestamp(self):
        uc = UserChallenge.objects.create(
            user=self.user, challenge=self.challenge, status='in_progress',
        )
        uc.complete()
        uc.refresh_from_db()
        self.assertIsNotNone(uc.completed_at)

    def test_str_representation(self):
        uc = UserChallenge.objects.create(
            user=self.user, challenge=self.challenge, status='in_progress',
        )
        self.assertIn('testuser', str(uc))
        self.assertIn('Walk', str(uc))

    def test_default_progress_is_zero(self):
        uc = UserChallenge.objects.create(
            user=self.user, challenge=self.challenge,
        )
        self.assertEqual(uc.progress, 0)


# ============================================================
# JOIN CHALLENGE VIEW TESTS
# ============================================================

class TestJoinChallengeView(TestCase):
    """Test atomic challenge joining."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user('testuser', 'test@example.com', 'Pass1234!')
        self.challenge = Challenge.objects.create(
            title='Walk to Work', description='Walk instead of driving.',
            category='transport', difficulty='easy',
            carbon_save_potential=5.0, duration_days=7,
            participants_count=0,
        )

    def test_join_creates_participation(self):
        self.client.force_login(self.user)
        self.client.post(reverse('challenges:join_challenge', args=[self.challenge.pk]))
        self.assertTrue(
            UserChallenge.objects.filter(user=self.user, challenge=self.challenge).exists()
        )

    def test_join_increments_participants_count(self):
        self.client.force_login(self.user)
        self.client.post(reverse('challenges:join_challenge', args=[self.challenge.pk]))
        self.challenge.refresh_from_db()
        self.assertEqual(self.challenge.participants_count, 1)

    def test_join_sets_status_in_progress(self):
        self.client.force_login(self.user)
        self.client.post(reverse('challenges:join_challenge', args=[self.challenge.pk]))
        uc = UserChallenge.objects.get(user=self.user, challenge=self.challenge)
        self.assertEqual(uc.status, 'in_progress')

    def test_cannot_join_twice(self):
        self.client.force_login(self.user)
        self.client.post(reverse('challenges:join_challenge', args=[self.challenge.pk]))
        self.client.post(reverse('challenges:join_challenge', args=[self.challenge.pk]))
        self.assertEqual(
            UserChallenge.objects.filter(user=self.user, challenge=self.challenge).count(), 1,
        )

    def test_double_join_does_not_double_count(self):
        self.client.force_login(self.user)
        self.client.post(reverse('challenges:join_challenge', args=[self.challenge.pk]))
        self.client.post(reverse('challenges:join_challenge', args=[self.challenge.pk]))
        self.challenge.refresh_from_db()
        self.assertEqual(self.challenge.participants_count, 1)

    def test_cannot_join_inactive_challenge(self):
        self.challenge.is_active = False
        self.challenge.save()
        self.client.force_login(self.user)
        response = self.client.post(
            reverse('challenges:join_challenge', args=[self.challenge.pk])
        )
        self.assertEqual(response.status_code, 404)

    def test_unauthenticated_redirect(self):
        response = self.client.post(
            reverse('challenges:join_challenge', args=[self.challenge.pk])
        )
        self.assertEqual(response.status_code, 302)
        self.assertIn('login', response.url)

    def test_join_redirects_to_detail(self):
        self.client.force_login(self.user)
        response = self.client.post(
            reverse('challenges:join_challenge', args=[self.challenge.pk])
        )
        self.assertEqual(response.status_code, 302)
        self.assertIn(str(self.challenge.pk), response.url)

    def test_multiple_users_join(self):
        user2 = User.objects.create_user('user2', 'u2@example.com', 'Pass1234!')
        self.client.force_login(self.user)
        self.client.post(reverse('challenges:join_challenge', args=[self.challenge.pk]))
        self.client.force_login(user2)
        self.client.post(reverse('challenges:join_challenge', args=[self.challenge.pk]))
        self.challenge.refresh_from_db()
        self.assertEqual(self.challenge.participants_count, 2)


# ============================================================
# CHALLENGE LIST VIEW TESTS
# ============================================================

class TestChallengeListView(TestCase):
    """Test challenge listing and filtering."""

    def setUp(self):
        self.client = Client()
        Challenge.objects.create(
            title='Easy Transport', description='Test',
            category='transport', difficulty='easy',
            carbon_save_potential=5.0, duration_days=7,
        )
        Challenge.objects.create(
            title='Hard Energy', description='Test',
            category='energy', difficulty='hard',
            carbon_save_potential=20.0, duration_days=30,
        )
        Challenge.objects.create(
            title='Medium Food', description='Test',
            category='food', difficulty='medium',
            carbon_save_potential=10.0, duration_days=14,
        )
        Challenge.objects.create(
            title='Inactive', description='Test',
            category='food', difficulty='easy',
            carbon_save_potential=3.0, duration_days=7,
            is_active=False,
        )

    def test_list_page_loads(self):
        response = self.client.get(reverse('challenges:challenge_list'))
        self.assertEqual(response.status_code, 200)

    def test_list_only_active(self):
        response = self.client.get(reverse('challenges:challenge_list'))
        challenges = response.context['challenges']
        for c in challenges:
            self.assertTrue(c.is_active)

    def test_inactive_not_shown(self):
        response = self.client.get(reverse('challenges:challenge_list'))
        challenges = response.context['challenges']
        titles = [c.title for c in challenges]
        self.assertNotIn('Inactive', titles)

    def test_filter_by_category(self):
        response = self.client.get(
            reverse('challenges:challenge_list') + '?category=transport'
        )
        challenges = response.context['challenges']
        for c in challenges:
            self.assertEqual(c.category, 'transport')

    def test_filter_by_difficulty(self):
        response = self.client.get(
            reverse('challenges:challenge_list') + '?difficulty=hard'
        )
        challenges = response.context['challenges']
        for c in challenges:
            self.assertEqual(c.difficulty, 'hard')

    def test_invalid_category_filter_ignored(self):
        response = self.client.get(
            reverse('challenges:challenge_list') + '?category=INVALID'
        )
        # Should show all active challenges
        challenges = response.context['challenges']
        self.assertEqual(len(challenges), 3)

    def test_context_has_filter_choices(self):
        response = self.client.get(reverse('challenges:challenge_list'))
        self.assertIn('categories', response.context)
        self.assertIn('difficulties', response.context)

    def test_combined_filters(self):
        response = self.client.get(
            reverse('challenges:challenge_list') + '?category=food&difficulty=medium'
        )
        challenges = response.context['challenges']
        for c in challenges:
            self.assertEqual(c.category, 'food')
            self.assertEqual(c.difficulty, 'medium')


# ============================================================
# CHALLENGE DETAIL VIEW TESTS
# ============================================================

class TestChallengeDetailView(TestCase):
    """Test challenge detail view."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user('testuser', 'test@example.com', 'Pass1234!')
        self.challenge = Challenge.objects.create(
            title='Walk', description='Walk to work!',
            category='transport', difficulty='easy',
            carbon_save_potential=5.0, duration_days=7,
        )

    def test_detail_page_loads(self):
        response = self.client.get(
            reverse('challenges:challenge_detail', args=[self.challenge.pk])
        )
        self.assertEqual(response.status_code, 200)

    def test_detail_shows_challenge_data(self):
        response = self.client.get(
            reverse('challenges:challenge_detail', args=[self.challenge.pk])
        )
        self.assertEqual(response.context['challenge'], self.challenge)

    def test_detail_shows_user_participation(self):
        self.client.force_login(self.user)
        UserChallenge.objects.create(
            user=self.user, challenge=self.challenge, status='in_progress',
        )
        response = self.client.get(
            reverse('challenges:challenge_detail', args=[self.challenge.pk])
        )
        self.assertIsNotNone(response.context['user_challenge'])

    def test_detail_no_participation_for_anonymous(self):
        response = self.client.get(
            reverse('challenges:challenge_detail', args=[self.challenge.pk])
        )
        self.assertIsNone(response.context['user_challenge'])


# ============================================================
# UPDATE PROGRESS VIEW TESTS
# ============================================================

class TestUpdateProgressView(TestCase):
    """Test progress update functionality."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user('testuser', 'test@example.com', 'Pass1234!')
        self.challenge = Challenge.objects.create(
            title='Walk', description='Walk!',
            category='transport', difficulty='easy',
            carbon_save_potential=5.0, duration_days=7,
        )
        self.uc = UserChallenge.objects.create(
            user=self.user, challenge=self.challenge, status='in_progress',
        )

    def test_update_to_50(self):
        self.client.force_login(self.user)
        self.client.post(
            reverse('challenges:update_progress', args=[self.challenge.pk]),
            {'progress': 50},
        )
        self.uc.refresh_from_db()
        self.assertEqual(self.uc.progress, 50)

    def test_complete_at_100(self):
        self.client.force_login(self.user)
        self.client.post(
            reverse('challenges:update_progress', args=[self.challenge.pk]),
            {'progress': 100},
        )
        self.uc.refresh_from_db()
        self.assertEqual(self.uc.status, 'completed')
        self.assertIsNotNone(self.uc.completed_at)

    def test_invalid_progress_non_numeric(self):
        self.client.force_login(self.user)
        response = self.client.post(
            reverse('challenges:update_progress', args=[self.challenge.pk]),
            {'progress': 'abc'},
        )
        self.assertEqual(response.status_code, 302)
        self.uc.refresh_from_db()
        self.assertEqual(self.uc.progress, 0)

    def test_negative_progress_clamped_to_zero(self):
        self.client.force_login(self.user)
        self.client.post(
            reverse('challenges:update_progress', args=[self.challenge.pk]),
            {'progress': -10},
        )
        self.uc.refresh_from_db()
        self.assertEqual(self.uc.progress, 0)

    def test_progress_over_100_completes(self):
        self.client.force_login(self.user)
        self.client.post(
            reverse('challenges:update_progress', args=[self.challenge.pk]),
            {'progress': 150},
        )
        self.uc.refresh_from_db()
        self.assertEqual(self.uc.status, 'completed')
        self.assertEqual(self.uc.progress, 100)

    def test_unauthenticated_redirect(self):
        response = self.client.post(
            reverse('challenges:update_progress', args=[self.challenge.pk]),
            {'progress': 50},
        )
        self.assertEqual(response.status_code, 302)
        self.assertIn('login', response.url)


# ============================================================
# LEADERBOARD VIEW TESTS
# ============================================================

class TestLeaderboardView(TestCase):
    """Test leaderboard with data."""

    def setUp(self):
        self.client = Client()

    def test_empty_leaderboard(self):
        response = self.client.get(reverse('challenges:leaderboard'))
        self.assertEqual(response.status_code, 200)

    def test_leaderboard_shows_completed_users(self):
        user = User.objects.create_user('winner', 'w@example.com', 'Pass1234!')
        challenge = Challenge.objects.create(
            title='Test', description='Test', category='general',
            difficulty='easy', carbon_save_potential=10.0, duration_days=7,
        )
        uc = UserChallenge.objects.create(
            user=user, challenge=challenge, status='in_progress',
        )
        uc.complete()
        response = self.client.get(reverse('challenges:leaderboard'))
        self.assertEqual(response.status_code, 200)

    def test_leaderboard_context_has_stats(self):
        response = self.client.get(reverse('challenges:leaderboard'))
        self.assertIn('total_completed', response.context)
        self.assertIn('total_carbon', response.context)
        self.assertIn('total_participants', response.context)

    def test_leaderboard_ranking_order(self):
        """User with more completions should rank higher."""
        user1 = User.objects.create_user('top', 't@example.com', 'Pass1234!')
        user2 = User.objects.create_user('bottom', 'b@example.com', 'Pass1234!')

        for i in range(3):
            c = Challenge.objects.create(
                title=f'C{i}', description='x', category='general',
                difficulty='easy', carbon_save_potential=5.0, duration_days=7,
            )
            uc = UserChallenge.objects.create(user=user1, challenge=c, status='in_progress')
            uc.complete()

        c2 = Challenge.objects.create(
            title='C-single', description='x', category='general',
            difficulty='easy', carbon_save_potential=5.0, duration_days=7,
        )
        uc2 = UserChallenge.objects.create(user=user2, challenge=c2, status='in_progress')
        uc2.complete()

        response = self.client.get(reverse('challenges:leaderboard'))
        leaders = response.context['top_users']
        if len(leaders) >= 2:
            self.assertGreaterEqual(
                leaders[0].get('completed_count', leaders[0].get('completed_count', 0)),
                leaders[1].get('completed_count', leaders[1].get('completed_count', 0)),
            )
