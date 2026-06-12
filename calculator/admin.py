"""Admin configuration for the calculator app."""
from django.contrib import admin
from .models import EmissionFactor, CarbonEntry


@admin.register(EmissionFactor)
class EmissionFactorAdmin(admin.ModelAdmin):
    """Admin interface for EmissionFactor model."""
    list_display = ('category', 'sub_category', 'factor', 'unit', 'source')
    list_filter = ('category', 'source')
    search_fields = ('sub_category', 'description')
    ordering = ('category', 'sub_category')


@admin.register(CarbonEntry)
class CarbonEntryAdmin(admin.ModelAdmin):
    """Admin interface for CarbonEntry model."""
    list_display = ('user', 'category', 'sub_category', 'value', 'unit', 'carbon_kg', 'date')
    list_filter = ('category', 'date', 'user')
    search_fields = ('user__username', 'sub_category', 'notes')
    date_hierarchy = 'date'
    ordering = ('-date', '-created_at')
    readonly_fields = ('created_at', 'updated_at')
