"""
Forms for the carbon footprint calculator.

Security:
- max_value prevents absurdly large submissions
- Future date validation
- Notes field length limit
"""

from django import forms
from django.utils import timezone

from .models import CarbonEntry
from .services import CarbonCalculatorService


class CarbonEntryForm(forms.Form):
    """Universal carbon entry form with server-side validation."""

    category = forms.ChoiceField(
        choices=[('', 'Select Category')] + CarbonEntry.CATEGORY_CHOICES,
        widget=forms.Select(attrs={
            'class': 'form-input',
            'aria-label': 'Emission category',
            'id': 'calc-category',
        })
    )
    sub_category = forms.CharField(
        max_length=50,
        widget=forms.Select(attrs={
            'class': 'form-input',
            'aria-label': 'Emission sub-category',
            'id': 'calc-subcategory',
        })
    )
    value = forms.FloatField(
        min_value=0,
        max_value=100000,
        widget=forms.NumberInput(attrs={
            'class': 'form-input',
            'placeholder': 'Enter amount',
            'aria-label': 'Quantity',
            'step': '0.01',
            'id': 'calc-value',
        })
    )
    date = forms.DateField(
        initial=timezone.now().date,
        widget=forms.DateInput(attrs={
            'class': 'form-input',
            'type': 'date',
            'aria-label': 'Date',
            'id': 'calc-date',
        })
    )
    notes = forms.CharField(
        required=False,
        max_length=1000,
        widget=forms.Textarea(attrs={
            'class': 'form-input',
            'rows': 3,
            'maxlength': '1000',
            'placeholder': 'Optional notes...',
            'aria-label': 'Additional notes',
            'id': 'calc-notes',
        })
    )

    def clean_sub_category(self):
        """Validate sub_category belongs to the selected category."""
        category = self.cleaned_data.get('category')
        sub_category = self.cleaned_data.get('sub_category')
        if category and sub_category:
            valid_subs = CarbonCalculatorService.get_subcategories(category)
            if sub_category not in valid_subs:
                raise forms.ValidationError(
                    'Invalid sub-category for selected category.'
                )
        return sub_category

    def clean_date(self):
        """Prevent future date entries."""
        date = self.cleaned_data.get('date')
        if date and date > timezone.now().date():
            raise forms.ValidationError('Date cannot be in the future.')
        return date
