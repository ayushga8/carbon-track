"""
Views for the Challenges application.

Security:
- Atomic challenge join with IntegrityError handling (no race condition)
- F() expressions for atomic counter updates
- Efficient leaderboard queries with caching
"""

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.models import User
from django.core.cache import cache
from django.db import IntegrityError, transaction
from django.db.models import Count, Sum, Q, Case, When, CharField, Value, F
from django.shortcuts import get_object_or_404, redirect
from django.utils import timezone
from django.views import View
from django.views.generic import ListView, DetailView

from .models import Challenge, UserChallenge


class ChallengeListView(ListView):
    """
    Display all active eco-challenges with optional filtering.

    Supports GET params:
      - category: filter by challenge category
      - difficulty: filter by difficulty level
    """

    model = Challenge
    template_name = 'challenges/challenge_list.html'
    context_object_name = 'challenges'
    paginate_by = 12

    def get_queryset(self):
        qs = Challenge.objects.filter(is_active=True)

        # Apply category filter
        category = self.request.GET.get('category')
        if category and category in dict(Challenge.CATEGORY_CHOICES):
            qs = qs.filter(category=category)

        # Apply difficulty filter
        difficulty = self.request.GET.get('difficulty')
        if difficulty and difficulty in dict(Challenge.DIFFICULTY_CHOICES):
            qs = qs.filter(difficulty=difficulty)

        # Annotate with user participation status
        if self.request.user.is_authenticated:
            qs = qs.annotate(
                user_status=Case(
                    When(
                        user_challenges__user=self.request.user,
                        user_challenges__status='completed',
                        then=Value('completed'),
                    ),
                    When(
                        user_challenges__user=self.request.user,
                        user_challenges__status='in_progress',
                        then=Value('in_progress'),
                    ),
                    default=Value('not_joined'),
                    output_field=CharField(),
                ),
            ).distinct()  # Prevent duplicates from annotation joins

        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['categories'] = Challenge.CATEGORY_CHOICES
        context['difficulties'] = Challenge.DIFFICULTY_CHOICES
        context['selected_category'] = self.request.GET.get('category', '')
        context['selected_difficulty'] = self.request.GET.get('difficulty', '')
        return context


class ChallengeDetailView(DetailView):
    """
    Display detailed information about a single challenge.
    Shows the user's participation status and progress.
    """

    model = Challenge
    template_name = 'challenges/challenge_detail.html'
    context_object_name = 'challenge'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.user.is_authenticated:
            try:
                user_challenge = UserChallenge.objects.get(
                    user=self.request.user,
                    challenge=self.object,
                )
                context['user_challenge'] = user_challenge
            except UserChallenge.DoesNotExist:
                context['user_challenge'] = None
        else:
            context['user_challenge'] = None
        return context


class JoinChallengeView(LoginRequiredMixin, View):
    """
    Handle POST request to join a challenge.

    Uses transaction.atomic + get_or_create for race-condition-safe joins.
    Uses F() expression for atomic participant count update.
    """

    def post(self, request, pk):
        challenge = get_object_or_404(Challenge, pk=pk, is_active=True)

        try:
            with transaction.atomic():
                # Atomic get_or_create prevents race conditions
                user_challenge, created = UserChallenge.objects.get_or_create(
                    user=request.user,
                    challenge=challenge,
                    defaults={
                        'status': 'in_progress',
                        'progress': 0,
                    },
                )

                if not created:
                    messages.warning(
                        request, 'You have already joined this challenge!'
                    )
                    return redirect('challenges:challenge_detail', pk=pk)

                # Atomic counter increment using F() expression
                Challenge.objects.filter(pk=pk).update(
                    participants_count=F('participants_count') + 1
                )

        except IntegrityError:
            messages.warning(
                request, 'You have already joined this challenge!'
            )
            return redirect('challenges:challenge_detail', pk=pk)

        messages.success(
            request,
            f'🎉 You joined "{challenge.title}"! Good luck!',
        )
        return redirect('challenges:challenge_detail', pk=pk)


class UpdateProgressView(LoginRequiredMixin, View):
    """
    Handle POST request to update challenge progress.
    Automatically marks completed when progress reaches 100.
    """

    def post(self, request, pk):
        challenge = get_object_or_404(Challenge, pk=pk)
        user_challenge = get_object_or_404(
            UserChallenge,
            user=request.user,
            challenge=challenge,
        )

        try:
            progress = int(request.POST.get('progress', 0))
            progress = max(0, min(100, progress))  # Clamp 0-100
        except (ValueError, TypeError):
            messages.error(request, 'Invalid progress value.')
            return redirect('challenges:challenge_detail', pk=pk)

        if progress >= 100:
            user_challenge.complete()
            messages.success(
                request,
                f'🏆 Congratulations! You completed "{challenge.title}"!',
            )
        else:
            user_challenge.progress = progress
            user_challenge.save(update_fields=['progress'])
            messages.success(
                request,
                f'Progress updated to {progress}%!',
            )

        return redirect('challenges:challenge_detail', pk=pk)


class LeaderboardView(ListView):
    """
    Display community leaderboard ranked by completed challenges.

    Uses Django's cache framework (5-minute TTL) and efficient annotations
    instead of N+1 queries in loops.
    """

    template_name = 'challenges/leaderboard.html'
    context_object_name = 'top_users'
    paginate_by = 50

    def get_queryset(self):
        cache_key = 'leaderboard_data'
        leaders = cache.get(cache_key)

        if leaders is None:
            leaders = list(
                User.objects.annotate(
                    completed_count=Count(
                        'user_challenges',
                        filter=Q(user_challenges__status='completed'),
                    ),
                    total_saved=Sum(
                        'user_challenges__challenge__carbon_save_potential',
                        filter=Q(user_challenges__status='completed'),
                    ),
                )
                .filter(completed_count__gt=0)
                .order_by('-completed_count', '-total_saved')
                .values('id', 'username', 'completed_count', 'total_saved')
            )
            cache.set(cache_key, leaders, 300)  # 5-minute cache

        return leaders

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Efficient community-wide stats in a single query
        stats = UserChallenge.objects.filter(
            status='completed'
        ).aggregate(
            total_completed=Count('id'),
            total_carbon=Sum('challenge__carbon_save_potential'),
        )

        context['total_completed'] = stats['total_completed'] or 0
        context['total_carbon'] = round(stats['total_carbon'] or 0, 1)
        context['total_participants'] = (
            User.objects.filter(user_challenges__isnull=False)
            .distinct()
            .count()
        )
        return context
