"""Models for the carbon footprint calculator."""
from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator


class EmissionFactor(models.Model):
    """Stores emission factors for various activities."""
    CATEGORY_CHOICES = [
        ('transport', 'Transportation'),
        ('energy', 'Home Energy'),
        ('food', 'Food & Diet'),
        ('shopping', 'Shopping'),
        ('waste', 'Waste'),
    ]
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    sub_category = models.CharField(max_length=50)
    factor = models.FloatField(help_text='kg CO2 per unit')
    unit = models.CharField(max_length=30)
    description = models.TextField(blank=True)
    source = models.CharField(max_length=200, default='EPA/DEFRA')

    def __str__(self):
        return f"{self.get_category_display()} - {self.sub_category} ({self.factor} kg CO2/{self.unit})"

    class Meta:
        unique_together = ['category', 'sub_category']
        ordering = ['category', 'sub_category']


class CarbonEntry(models.Model):
    """Individual carbon footprint entry by a user."""
    CATEGORY_CHOICES = EmissionFactor.CATEGORY_CHOICES

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='carbon_entries')
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, db_index=True)
    sub_category = models.CharField(max_length=50)
    value = models.FloatField(validators=[MinValueValidator(0)])
    unit = models.CharField(max_length=30)
    carbon_kg = models.FloatField(help_text='Calculated CO2 in kg')
    date = models.DateField(db_index=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username} - {self.sub_category}: {self.carbon_kg:.2f} kg CO2"

    class Meta:
        ordering = ['-date', '-created_at']
        verbose_name_plural = 'Carbon entries'
        indexes = [
            models.Index(fields=['user', 'date']),
            models.Index(fields=['user', 'category']),
        ]
