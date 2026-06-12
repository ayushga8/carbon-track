"""
Models for the Challenges application.

Defines Challenge and UserChallenge models for the eco-challenge
tracking system where users can participate in carbon-reducing activities.
"""

from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone


class Challenge(models.Model):
    """
    Represents an eco-challenge that users can participate in.

    Each challenge has a category, difficulty level, estimated carbon
    savings, and a duration. Active challenges are displayed to users.
    """

    DIFFICULTY_CHOICES = [
        ('easy', 'Easy'),
        ('medium', 'Medium'),
        ('hard', 'Hard'),
    ]
    CATEGORY_CHOICES = [
        ('transport', 'Transportation'),
        ('energy', 'Home Energy'),
        ('food', 'Food & Diet'),
        ('shopping', 'Shopping'),
        ('waste', 'Waste'),
        ('general', 'General'),
    ]

    title = models.CharField(max_length=200)
    description = models.TextField()
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, db_index=True)
    difficulty = models.CharField(max_length=10, choices=DIFFICULTY_CHOICES, db_index=True)
    carbon_save_potential = models.DecimalField(
        max_digits=8, decimal_places=2,
        help_text='Estimated kg CO2 saved',
        validators=[MinValueValidator(0)],
    )
    duration_days = models.IntegerField(validators=[MinValueValidator(1)])
    icon = models.CharField(max_length=10, default='🌱')
    is_active = models.BooleanField(default=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    participants_count = models.IntegerField(default=0)

    def __str__(self):
        return self.title

    class Meta:
        ordering = ['-created_at']


class UserChallenge(models.Model):
    """
    Tracks a user's participation in a specific challenge.

    Records progress (0-100%), status, and completion timestamp.
    Each user can only join a challenge once (unique_together constraint).
    """

    STATUS_CHOICES = [
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('abandoned', 'Abandoned'),
    ]

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='user_challenges',
    )
    challenge = models.ForeignKey(
        Challenge,
        on_delete=models.CASCADE,
        related_name='user_challenges',
    )
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    progress = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='in_progress',
        db_index=True,
    )
    notes = models.TextField(blank=True)

    def __str__(self):
        return f"{self.user.username} - {self.challenge.title} ({self.status})"

    def complete(self):
        """Mark this challenge as completed with current timestamp."""
        self.status = 'completed'
        self.progress = 100
        self.completed_at = timezone.now()
        self.save(update_fields=['status', 'progress', 'completed_at'])

    class Meta:
        unique_together = ['user', 'challenge']
        ordering = ['-started_at']
        indexes = [
            models.Index(fields=['challenge', 'status']),
            models.Index(fields=['user', 'status']),
        ]
