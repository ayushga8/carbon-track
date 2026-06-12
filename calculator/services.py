"""Business logic for carbon footprint calculations."""
from django.db.models import Sum, Avg, Count
from django.db.models.functions import TruncDay, TruncWeek, TruncMonth
from .models import EmissionFactor, CarbonEntry


class CarbonCalculatorService:
    """Business logic for carbon footprint calculations."""

    # Default emission factors (kg CO2 per unit) - used as fallback
    DEFAULT_FACTORS = {
        'transport': {
            'car_petrol': {'factor': 0.21, 'unit': 'km', 'desc': 'Petrol car driving'},
            'car_diesel': {'factor': 0.27, 'unit': 'km', 'desc': 'Diesel car driving'},
            'car_electric': {'factor': 0.05, 'unit': 'km', 'desc': 'Electric car driving'},
            'bus': {'factor': 0.089, 'unit': 'km', 'desc': 'Bus travel'},
            'train': {'factor': 0.041, 'unit': 'km', 'desc': 'Train travel'},
            'flight_domestic': {'factor': 0.255, 'unit': 'km', 'desc': 'Domestic flight'},
            'flight_international': {'factor': 0.195, 'unit': 'km', 'desc': 'International flight'},
            'bicycle': {'factor': 0.0, 'unit': 'km', 'desc': 'Cycling'},
            'walking': {'factor': 0.0, 'unit': 'km', 'desc': 'Walking'},
            'motorcycle': {'factor': 0.113, 'unit': 'km', 'desc': 'Motorcycle'},
        },
        'energy': {
            'electricity': {'factor': 0.85, 'unit': 'kWh', 'desc': 'Electricity consumption'},
            'natural_gas': {'factor': 2.0, 'unit': 'cubic_m', 'desc': 'Natural gas'},
            'lpg': {'factor': 1.51, 'unit': 'litre', 'desc': 'LPG cooking gas'},
            'coal': {'factor': 2.42, 'unit': 'kg', 'desc': 'Coal burning'},
            'solar': {'factor': 0.0, 'unit': 'kWh', 'desc': 'Solar energy'},
        },
        'food': {
            'beef': {'factor': 27.0, 'unit': 'kg', 'desc': 'Beef consumption'},
            'chicken': {'factor': 6.9, 'unit': 'kg', 'desc': 'Chicken consumption'},
            'fish': {'factor': 5.4, 'unit': 'kg', 'desc': 'Fish consumption'},
            'dairy': {'factor': 3.2, 'unit': 'kg', 'desc': 'Dairy products'},
            'vegetables': {'factor': 0.4, 'unit': 'kg', 'desc': 'Vegetables'},
            'fruits': {'factor': 0.5, 'unit': 'kg', 'desc': 'Fruits'},
            'rice': {'factor': 2.7, 'unit': 'kg', 'desc': 'Rice'},
            'bread': {'factor': 0.8, 'unit': 'kg', 'desc': 'Bread/wheat products'},
        },
        'shopping': {
            'clothing': {'factor': 15.0, 'unit': 'item', 'desc': 'New clothing item'},
            'electronics': {'factor': 50.0, 'unit': 'item', 'desc': 'Electronic device'},
            'furniture': {'factor': 100.0, 'unit': 'item', 'desc': 'Furniture piece'},
            'plastic_bags': {'factor': 0.033, 'unit': 'bag', 'desc': 'Plastic bag'},
            'online_order': {'factor': 3.0, 'unit': 'package', 'desc': 'Online delivery package'},
        },
        'waste': {
            'general_waste': {'factor': 0.587, 'unit': 'kg', 'desc': 'General waste to landfill'},
            'recycling': {'factor': 0.021, 'unit': 'kg', 'desc': 'Recycled waste'},
            'composting': {'factor': 0.01, 'unit': 'kg', 'desc': 'Composted organic waste'},
            'food_waste': {'factor': 2.53, 'unit': 'kg', 'desc': 'Food waste to landfill'},
        },
    }

    @classmethod
    def get_emission_factor(cls, category, sub_category):
        """Get emission factor from database or defaults."""
        try:
            ef = EmissionFactor.objects.get(category=category, sub_category=sub_category)
            return ef.factor, ef.unit
        except EmissionFactor.DoesNotExist:
            defaults = cls.DEFAULT_FACTORS.get(category, {})
            sub = defaults.get(sub_category, {})
            return sub.get('factor', 0), sub.get('unit', 'unit')

    @classmethod
    def calculate_carbon(cls, category, sub_category, value):
        """Calculate carbon emissions for a given activity."""
        factor, unit = cls.get_emission_factor(category, sub_category)
        return round(value * factor, 3)

    @classmethod
    def get_subcategories(cls, category):
        """Get available sub-categories for a category."""
        return cls.DEFAULT_FACTORS.get(category, {})

    @classmethod
    def get_all_categories(cls):
        """Get all category choices."""
        return EmissionFactor.CATEGORY_CHOICES
