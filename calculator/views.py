"""Views for the carbon footprint calculator."""
import json
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse, Http404
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import FormView, ListView, DetailView, DeleteView

from .forms import CarbonEntryForm
from .models import CarbonEntry
from .services import CarbonCalculatorService


class CalculatorView(LoginRequiredMixin, FormView):
    """Main calculator form view for logging carbon emissions."""
    template_name = 'calculator/calculator.html'
    form_class = CarbonEntryForm
    success_url = reverse_lazy('calculator:entry_list')

    def form_valid(self, form):
        """Process valid form: calculate carbon and create entry."""
        category = form.cleaned_data['category']
        sub_category = form.cleaned_data['sub_category']
        value = form.cleaned_data['value']
        date = form.cleaned_data['date']
        notes = form.cleaned_data.get('notes', '')

        # Calculate carbon emissions
        carbon_kg = CarbonCalculatorService.calculate_carbon(category, sub_category, value)
        _, unit = CarbonCalculatorService.get_emission_factor(category, sub_category)

        # Create entry
        CarbonEntry.objects.create(
            user=self.request.user,
            category=category,
            sub_category=sub_category,
            value=value,
            unit=unit,
            carbon_kg=carbon_kg,
            date=date,
            notes=notes,
        )

        messages.success(
            self.request,
            f'Entry logged! {value} {unit} of {sub_category.replace("_", " ")} '
            f'= {carbon_kg:.2f} kg CO2'
        )
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        """Add category data to context."""
        context = super().get_context_data(**kwargs)
        context['categories'] = CarbonCalculatorService.get_all_categories()
        context['all_factors'] = json.dumps(CarbonCalculatorService.DEFAULT_FACTORS)
        return context


class EntryListView(LoginRequiredMixin, ListView):
    """List all carbon entries for the current user with filtering."""
    template_name = 'calculator/entry_list.html'
    context_object_name = 'entries'
    paginate_by = 15

    def get_queryset(self):
        """Filter entries by user and optional GET params."""
        qs = CarbonEntry.objects.filter(user=self.request.user).order_by('-date', '-created_at')

        # Filter by category
        category = self.request.GET.get('category')
        if category and category in dict(CarbonEntry.CATEGORY_CHOICES):
            qs = qs.filter(category=category)

        # Filter by date range
        date_from = self.request.GET.get('date_from')
        date_to = self.request.GET.get('date_to')
        if date_from:
            qs = qs.filter(date__gte=date_from)
        if date_to:
            qs = qs.filter(date__lte=date_to)

        return qs

    def get_context_data(self, **kwargs):
        """Add summary statistics and filter options to context."""
        context = super().get_context_data(**kwargs)
        user_entries = CarbonEntry.objects.filter(user=self.request.user)

        from django.db.models import Sum, Avg, Count

        stats = user_entries.aggregate(
            total_entries=Count('id'),
            total_co2=Sum('carbon_kg'),
            avg_co2=Avg('carbon_kg'),
        )
        context['total_entries'] = stats['total_entries'] or 0
        context['total_co2'] = round(stats['total_co2'] or 0, 2)
        context['avg_co2'] = round(stats['avg_co2'] or 0, 2)
        context['categories'] = CarbonEntry.CATEGORY_CHOICES
        context['selected_category'] = self.request.GET.get('category', '')
        context['date_from'] = self.request.GET.get('date_from', '')
        context['date_to'] = self.request.GET.get('date_to', '')
        return context


class EntryDetailView(LoginRequiredMixin, DetailView):
    """Display details of a single carbon entry."""
    template_name = 'calculator/entry_detail.html'
    context_object_name = 'entry'
    model = CarbonEntry

    def get_queryset(self):
        """Ensure users can only see their own entries."""
        return CarbonEntry.objects.filter(user=self.request.user)


class EntryDeleteView(LoginRequiredMixin, DeleteView):
    """Delete a carbon entry with confirmation."""
    template_name = 'calculator/entry_confirm_delete.html'
    context_object_name = 'entry'
    success_url = reverse_lazy('calculator:entry_list')

    def get_queryset(self):
        """Ensure users can only delete their own entries."""
        return CarbonEntry.objects.filter(user=self.request.user)

    def delete(self, request, *args, **kwargs):
        """Add success message on delete."""
        messages.success(request, 'Carbon entry deleted successfully.')
        return super().delete(request, *args, **kwargs)


class SubcategoryAPIView(LoginRequiredMixin, View):
    """API endpoint returning subcategories for a given category as JSON."""

    def get(self, request, category):
        """Return subcategory list with value, label, unit, and factor."""
        subcategories = CarbonCalculatorService.get_subcategories(category)
        if not subcategories:
            return JsonResponse({'error': 'Invalid category'}, status=400)

        result = []
        for key, data in subcategories.items():
            result.append({
                'value': key,
                'label': data['desc'],
                'unit': data['unit'],
                'factor': data['factor'],
            })

        return JsonResponse(result, safe=False)
