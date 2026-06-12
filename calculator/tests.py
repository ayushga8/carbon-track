"""
Comprehensive tests for the calculator app.

~35 tests covering services, forms, views, API, edge cases.
"""

from datetime import date, timedelta
from django.contrib.auth.models import User
from django.db.models import Sum
from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone

from .forms import CarbonEntryForm
from .models import CarbonEntry, EmissionFactor
from .services import CarbonCalculatorService


# ============================================================
# SERVICE TESTS
# ============================================================

class TestCarbonCalculatorService(TestCase):
    """Test emission calculation service."""

    def test_calculate_carbon_petrol_car(self):
        result = CarbonCalculatorService.calculate_carbon('transport', 'car_petrol', 100)
        self.assertEqual(result, 21.0)

    def test_calculate_carbon_bicycle_zero(self):
        result = CarbonCalculatorService.calculate_carbon('transport', 'bicycle', 50)
        self.assertEqual(result, 0.0)

    def test_calculate_carbon_bus(self):
        result = CarbonCalculatorService.calculate_carbon('transport', 'bus', 100)
        self.assertEqual(result, 8.9)

    def test_calculate_carbon_electricity(self):
        result = CarbonCalculatorService.calculate_carbon('energy', 'electricity', 100)
        self.assertEqual(result, 85.0)

    def test_calculate_carbon_beef(self):
        result = CarbonCalculatorService.calculate_carbon('food', 'beef', 1)
        self.assertEqual(result, 27.0)

    def test_calculate_carbon_zero_value(self):
        result = CarbonCalculatorService.calculate_carbon('transport', 'car_petrol', 0)
        self.assertEqual(result, 0.0)

    def test_calculate_carbon_decimal_value(self):
        result = CarbonCalculatorService.calculate_carbon('transport', 'car_petrol', 10.5)
        self.assertEqual(result, 2.205)

    def test_get_subcategories_transport(self):
        subs = CarbonCalculatorService.get_subcategories('transport')
        self.assertIn('car_petrol', subs)
        self.assertIn('bus', subs)
        self.assertIn('train', subs)
        self.assertIn('bicycle', subs)

    def test_get_subcategories_energy(self):
        subs = CarbonCalculatorService.get_subcategories('energy')
        self.assertIn('electricity', subs)

    def test_get_subcategories_food(self):
        subs = CarbonCalculatorService.get_subcategories('food')
        self.assertIn('beef', subs)
        self.assertIn('vegetables', subs)

    def test_get_subcategories_invalid_category(self):
        subs = CarbonCalculatorService.get_subcategories('nonexistent')
        self.assertEqual(subs, {})

    def test_get_emission_factor_from_db(self):
        EmissionFactor.objects.create(
            category='transport',
            sub_category='car_petrol',
            factor=0.25,
            unit='km',
        )
        factor, unit = CarbonCalculatorService.get_emission_factor('transport', 'car_petrol')
        self.assertEqual(factor, 0.25)
        self.assertEqual(unit, 'km')

    def test_get_emission_factor_fallback(self):
        factor, unit = CarbonCalculatorService.get_emission_factor('transport', 'bus')
        self.assertEqual(factor, 0.089)
        self.assertEqual(unit, 'km')

    def test_get_emission_factor_unknown_sub(self):
        factor, unit = CarbonCalculatorService.get_emission_factor('transport', 'unknown')
        self.assertEqual(factor, 0)

    def test_get_all_categories(self):
        cats = CarbonCalculatorService.get_all_categories()
        cat_keys = [c[0] for c in cats]
        self.assertIn('transport', cat_keys)
        self.assertIn('energy', cat_keys)
        self.assertIn('food', cat_keys)

    def test_all_categories_have_subcategories(self):
        """Every category in DEFAULT_FACTORS should have at least one sub."""
        for cat in CarbonCalculatorService.DEFAULT_FACTORS:
            subs = CarbonCalculatorService.get_subcategories(cat)
            self.assertGreater(len(subs), 0, f"Category '{cat}' has no subcategories")


# ============================================================
# FORM TESTS
# ============================================================

class TestCarbonEntryForm(TestCase):
    """Test calculator form validation."""

    def get_valid_data(self):
        return {
            'category': 'transport',
            'sub_category': 'car_petrol',
            'value': 50,
            'date': date.today().isoformat(),
            'notes': 'Test entry',
        }

    def test_valid_form(self):
        form = CarbonEntryForm(data=self.get_valid_data())
        self.assertTrue(form.is_valid())

    def test_negative_value_rejected(self):
        data = self.get_valid_data()
        data['value'] = -10
        form = CarbonEntryForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn('value', form.errors)

    def test_zero_value_accepted(self):
        data = self.get_valid_data()
        data['value'] = 0
        form = CarbonEntryForm(data=data)
        self.assertTrue(form.is_valid())

    def test_extremely_large_value_rejected(self):
        data = self.get_valid_data()
        data['value'] = 999999
        form = CarbonEntryForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn('value', form.errors)

    def test_max_value_boundary_accepted(self):
        data = self.get_valid_data()
        data['value'] = 100000
        form = CarbonEntryForm(data=data)
        self.assertTrue(form.is_valid())

    def test_future_date_rejected(self):
        data = self.get_valid_data()
        data['date'] = (date.today() + timedelta(days=5)).isoformat()
        form = CarbonEntryForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn('date', form.errors)

    def test_today_date_accepted(self):
        data = self.get_valid_data()
        data['date'] = date.today().isoformat()
        form = CarbonEntryForm(data=data)
        self.assertTrue(form.is_valid())

    def test_past_date_accepted(self):
        data = self.get_valid_data()
        data['date'] = (date.today() - timedelta(days=30)).isoformat()
        form = CarbonEntryForm(data=data)
        self.assertTrue(form.is_valid())

    def test_invalid_subcategory_rejected(self):
        data = self.get_valid_data()
        data['sub_category'] = 'nonexistent_sub'
        form = CarbonEntryForm(data=data)
        self.assertFalse(form.is_valid())

    def test_notes_max_length_exceeded(self):
        data = self.get_valid_data()
        data['notes'] = 'x' * 1001
        form = CarbonEntryForm(data=data)
        self.assertFalse(form.is_valid())

    def test_notes_at_max_length_accepted(self):
        data = self.get_valid_data()
        data['notes'] = 'x' * 1000
        form = CarbonEntryForm(data=data)
        self.assertTrue(form.is_valid())

    def test_empty_notes_accepted(self):
        data = self.get_valid_data()
        data['notes'] = ''
        form = CarbonEntryForm(data=data)
        self.assertTrue(form.is_valid())

    def test_empty_category_rejected(self):
        data = self.get_valid_data()
        data['category'] = ''
        form = CarbonEntryForm(data=data)
        self.assertFalse(form.is_valid())


# ============================================================
# MODEL TESTS
# ============================================================

class TestCarbonEntryModel(TestCase):
    """Test CarbonEntry model."""

    def setUp(self):
        self.user = User.objects.create_user('testuser', 'test@example.com', 'Pass1234!')

    def test_entry_str(self):
        entry = CarbonEntry.objects.create(
            user=self.user, category='transport', sub_category='car_petrol',
            value=10, unit='km', carbon_kg=2.1, date=date.today(),
        )
        self.assertIn('testuser', str(entry))
        self.assertIn('car_petrol', str(entry))

    def test_entry_ordering(self):
        CarbonEntry.objects.create(
            user=self.user, category='transport', sub_category='bus',
            value=10, unit='km', carbon_kg=0.89,
            date=date.today() - timedelta(days=1),
        )
        CarbonEntry.objects.create(
            user=self.user, category='food', sub_category='beef',
            value=1, unit='kg', carbon_kg=27.0, date=date.today(),
        )
        entries = CarbonEntry.objects.filter(user=self.user)
        self.assertEqual(entries[0].date, date.today())


class TestEmissionFactorModel(TestCase):
    """Test EmissionFactor model."""

    def test_unique_together(self):
        EmissionFactor.objects.create(
            category='transport', sub_category='car_petrol', factor=0.21, unit='km',
        )
        from django.db import IntegrityError
        with self.assertRaises(IntegrityError):
            EmissionFactor.objects.create(
                category='transport', sub_category='car_petrol', factor=0.25, unit='km',
            )

    def test_str_representation(self):
        ef = EmissionFactor.objects.create(
            category='transport', sub_category='car_petrol', factor=0.21, unit='km',
        )
        self.assertIn('Transportation', str(ef))
        self.assertIn('car_petrol', str(ef))


# ============================================================
# VIEW TESTS
# ============================================================

class TestCalculatorView(TestCase):
    """Test calculator view."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user('testuser', 'test@example.com', 'Pass1234!')

    def test_unauthenticated_redirect(self):
        response = self.client.get(reverse('calculator:calculator'))
        self.assertEqual(response.status_code, 302)

    def test_authenticated_get(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse('calculator:calculator'))
        self.assertEqual(response.status_code, 200)

    def test_context_has_categories(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse('calculator:calculator'))
        self.assertIn('categories', response.context)

    def test_successful_entry_creation(self):
        self.client.force_login(self.user)
        response = self.client.post(reverse('calculator:calculator'), {
            'category': 'transport',
            'sub_category': 'car_petrol',
            'value': 50,
            'date': date.today().isoformat(),
            'notes': '',
        })
        self.assertEqual(response.status_code, 302)
        self.assertEqual(CarbonEntry.objects.filter(user=self.user).count(), 1)

    def test_entry_calculates_carbon_correctly(self):
        self.client.force_login(self.user)
        self.client.post(reverse('calculator:calculator'), {
            'category': 'transport',
            'sub_category': 'car_petrol',
            'value': 100,
            'date': date.today().isoformat(),
            'notes': '',
        })
        entry = CarbonEntry.objects.get(user=self.user)
        self.assertEqual(entry.carbon_kg, 21.0)


class TestEntryListView(TestCase):
    """Test entry list view."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user('testuser', 'test@example.com', 'Pass1234!')
        self.other_user = User.objects.create_user('other', 'other@example.com', 'Pass1234!')

        for i in range(5):
            CarbonEntry.objects.create(
                user=self.user, category='transport', sub_category='car_petrol',
                value=10, unit='km', carbon_kg=2.1,
                date=date.today() - timedelta(days=i),
            )
        CarbonEntry.objects.create(
            user=self.user, category='food', sub_category='beef',
            value=1, unit='kg', carbon_kg=27.0, date=date.today(),
        )
        CarbonEntry.objects.create(
            user=self.other_user, category='food', sub_category='beef',
            value=1, unit='kg', carbon_kg=27.0, date=date.today(),
        )

    def test_user_isolation(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse('calculator:entry_list'))
        entries = response.context['entries']
        for entry in entries:
            self.assertEqual(entry.user, self.user)

    def test_entry_count(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse('calculator:entry_list'))
        self.assertEqual(response.context['total_entries'], 6)

    def test_filter_by_category(self):
        self.client.force_login(self.user)
        response = self.client.get(
            reverse('calculator:entry_list') + '?category=food'
        )
        entries = response.context['entries']
        for entry in entries:
            self.assertEqual(entry.category, 'food')

    def test_cannot_delete_others_entry(self):
        self.client.force_login(self.user)
        other_entry = CarbonEntry.objects.filter(user=self.other_user).first()
        response = self.client.post(
            reverse('calculator:entry_delete', args=[other_entry.pk])
        )
        self.assertEqual(response.status_code, 404)

    def test_can_delete_own_entry(self):
        self.client.force_login(self.user)
        own_entry = CarbonEntry.objects.filter(user=self.user).first()
        response = self.client.post(
            reverse('calculator:entry_delete', args=[own_entry.pk])
        )
        self.assertEqual(response.status_code, 302)
        self.assertFalse(CarbonEntry.objects.filter(pk=own_entry.pk).exists())

    def test_context_has_stats(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse('calculator:entry_list'))
        self.assertIn('total_co2', response.context)
        self.assertIn('avg_co2', response.context)


class TestEntryDetailView(TestCase):
    """Test entry detail view."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user('testuser', 'test@example.com', 'Pass1234!')
        self.other_user = User.objects.create_user('other', 'other@example.com', 'Pass1234!')
        self.entry = CarbonEntry.objects.create(
            user=self.user, category='transport', sub_category='car_petrol',
            value=10, unit='km', carbon_kg=2.1, date=date.today(),
        )
        self.other_entry = CarbonEntry.objects.create(
            user=self.other_user, category='food', sub_category='beef',
            value=1, unit='kg', carbon_kg=27.0, date=date.today(),
        )

    def test_view_own_entry(self):
        self.client.force_login(self.user)
        response = self.client.get(
            reverse('calculator:entry_detail', args=[self.entry.pk])
        )
        self.assertEqual(response.status_code, 200)

    def test_cannot_view_others_entry(self):
        self.client.force_login(self.user)
        response = self.client.get(
            reverse('calculator:entry_detail', args=[self.other_entry.pk])
        )
        self.assertEqual(response.status_code, 404)


class TestSubcategoryAPI(TestCase):
    """Test subcategory API endpoint."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user('testuser', 'test@example.com', 'Pass1234!')

    def test_valid_category_returns_list(self):
        self.client.force_login(self.user)
        response = self.client.get(
            reverse('calculator:subcategories_api', args=['transport'])
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIsInstance(data, list)
        self.assertGreater(len(data), 0)

    def test_subcategory_has_required_fields(self):
        self.client.force_login(self.user)
        response = self.client.get(
            reverse('calculator:subcategories_api', args=['transport'])
        )
        data = response.json()
        for item in data:
            self.assertIn('value', item)
            self.assertIn('label', item)
            self.assertIn('unit', item)
            self.assertIn('factor', item)

    def test_invalid_category_returns_400(self):
        self.client.force_login(self.user)
        response = self.client.get(
            reverse('calculator:subcategories_api', args=['invalid'])
        )
        self.assertEqual(response.status_code, 400)

    def test_unauthenticated_redirect(self):
        response = self.client.get(
            reverse('calculator:subcategories_api', args=['transport'])
        )
        self.assertEqual(response.status_code, 302)
