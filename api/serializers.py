"""
REST Framework serializers for the Carbon Footprint API.
"""
from rest_framework import serializers
from calculator.models import CarbonEntry
from challenges.models import Challenge, UserChallenge


class CarbonEntrySerializer(serializers.ModelSerializer):
    """Serializer for individual carbon entries."""
    class Meta:
        model = CarbonEntry
        fields = [
            'id', 'category', 'sub_category', 'value',
            'unit', 'carbon_kg', 'date', 'notes', 'created_at',
        ]
        read_only_fields = ['id', 'carbon_kg', 'created_at']


class CarbonStatsSerializer(serializers.Serializer):
    """Serializer for aggregated carbon stats."""
    total_carbon = serializers.FloatField()
    monthly_carbon = serializers.FloatField()
    weekly_carbon = serializers.FloatField()
    entry_count = serializers.IntegerField()
    average_daily = serializers.FloatField()


class CategoryBreakdownSerializer(serializers.Serializer):
    """Serializer for category breakdown data."""
    category = serializers.CharField()
    total = serializers.FloatField()
    count = serializers.IntegerField()


class TrendDataSerializer(serializers.Serializer):
    """Serializer for trend data points."""
    day = serializers.DateField(required=False)
    week = serializers.DateField(required=False)
    month = serializers.DateField(required=False)
    total = serializers.FloatField()


class ChallengeSerializer(serializers.ModelSerializer):
    """Serializer for challenges."""
    class Meta:
        model = Challenge
        fields = [
            'id', 'title', 'description', 'category', 'difficulty',
            'carbon_save_potential', 'duration_days', 'icon',
            'participants_count', 'is_active',
        ]


class LeaderboardEntrySerializer(serializers.Serializer):
    """Serializer for leaderboard entries."""
    rank = serializers.IntegerField()
    username = serializers.CharField()
    challenges_completed = serializers.IntegerField()
    carbon_saved = serializers.FloatField()
