"""
Management command to seed the database with eco-challenges.

Populates 12 diverse challenges across different categories and
difficulty levels. Uses update_or_create for idempotency.
"""

from django.core.management.base import BaseCommand

from challenges.models import Challenge


CHALLENGES_DATA = [
    {
        'title': 'Car-Free Week',
        'icon': '🚲',
        'category': 'transport',
        'difficulty': 'easy',
        'duration_days': 7,
        'carbon_save_potential': 25.0,
        'description': (
            'Ditch the car for a full week! Walk, cycle, or use public '
            'transport for all your trips. You\'ll reduce emissions and '
            'discover new ways to get around your city while improving '
            'your health and saving money on fuel.'
        ),
    },
    {
        'title': 'Meatless Monday',
        'icon': '🥦',
        'category': 'food',
        'difficulty': 'easy',
        'duration_days': 30,
        'carbon_save_potential': 15.0,
        'description': (
            'Go meat-free every Monday for a whole month! Animal '
            'agriculture is a leading contributor to greenhouse gas '
            'emissions. Explore delicious plant-based recipes and reduce '
            'your food carbon footprint one day at a time.'
        ),
    },
    {
        'title': 'Energy Saver',
        'icon': '💡',
        'category': 'energy',
        'difficulty': 'medium',
        'duration_days': 14,
        'carbon_save_potential': 20.0,
        'description': (
            'Cut your home energy consumption for two weeks. Turn off '
            'lights when leaving rooms, use natural ventilation, limit '
            'AC usage, switch to LED bulbs, and run appliances on '
            'energy-saving mode. Track your electricity meter daily!'
        ),
    },
    {
        'title': 'Zero Waste Week',
        'icon': '♻️',
        'category': 'waste',
        'difficulty': 'medium',
        'duration_days': 7,
        'carbon_save_potential': 10.0,
        'description': (
            'Produce as close to zero landfill waste as possible for '
            'one week. Compost organic scraps, refuse single-use items, '
            'recycle everything recyclable, and bring reusable bags, '
            'bottles, and containers everywhere you go.'
        ),
    },
    {
        'title': 'Walk 10K Steps Daily',
        'icon': '🚶',
        'category': 'transport',
        'difficulty': 'easy',
        'duration_days': 30,
        'carbon_save_potential': 30.0,
        'description': (
            'Walk at least 10,000 steps every day for a month. Replace '
            'short car trips with walks, take the stairs, and enjoy the '
            'outdoors. Great for your health and the planet — every step '
            'is a step away from carbon emissions.'
        ),
    },
    {
        'title': 'Plant-Based Month',
        'icon': '🌱',
        'category': 'food',
        'difficulty': 'hard',
        'duration_days': 30,
        'carbon_save_potential': 45.0,
        'description': (
            'Go fully plant-based for 30 days! No meat, dairy, or eggs. '
            'A plant-based diet can reduce your food-related carbon '
            'footprint by up to 73%%. Explore amazing vegan recipes and '
            'discover the power of plants.'
        ),
    },
    {
        'title': 'Unplug Challenge',
        'icon': '🔌',
        'category': 'energy',
        'difficulty': 'easy',
        'duration_days': 7,
        'carbon_save_potential': 8.0,
        'description': (
            'Unplug all devices and chargers when not in use for a week. '
            'Phantom energy from plugged-in electronics accounts for up '
            'to 10%% of household electricity use. Use power strips and '
            'make unplugging a habit.'
        ),
    },
    {
        'title': 'No New Clothes',
        'icon': '🛍️',
        'category': 'shopping',
        'difficulty': 'medium',
        'duration_days': 30,
        'carbon_save_potential': 35.0,
        'description': (
            'Commit to buying zero new clothing for one month. The '
            'fashion industry produces 10%% of global emissions. Swap '
            'clothes with friends, visit thrift stores, or repair what '
            'you already own instead.'
        ),
    },
    {
        'title': 'Zero Food Waste',
        'icon': '🥡',
        'category': 'waste',
        'difficulty': 'hard',
        'duration_days': 14,
        'carbon_save_potential': 18.0,
        'description': (
            'Waste no food for two weeks. Plan meals carefully, store '
            'food properly, use leftovers creatively, and compost any '
            'unavoidable scraps. Food waste in landfills produces methane, '
            'a potent greenhouse gas.'
        ),
    },
    {
        'title': 'Public Transport Only',
        'icon': '🚊',
        'category': 'transport',
        'difficulty': 'medium',
        'duration_days': 14,
        'carbon_save_potential': 40.0,
        'description': (
            'Use only public transport for two weeks — no personal cars '
            'or ride-shares. Buses, trains, and metros emit far less CO₂ '
            'per passenger than individual vehicles. Discover efficient '
            'routes in your city!'
        ),
    },
    {
        'title': 'Minimal Packaging',
        'icon': '📦',
        'category': 'shopping',
        'difficulty': 'easy',
        'duration_days': 7,
        'carbon_save_potential': 5.0,
        'description': (
            'Buy products with minimal or no packaging for a week. Bring '
            'your own containers to the store, shop at farmers\' markets, '
            'choose package-free alternatives, and say no to plastic bags '
            'and unnecessary wrapping.'
        ),
    },
    {
        'title': 'Carbon Neutral Day',
        'icon': '🌍',
        'category': 'general',
        'difficulty': 'hard',
        'duration_days': 1,
        'carbon_save_potential': 12.0,
        'description': (
            'Attempt to live one day with zero net carbon emissions! '
            'Walk or cycle everywhere, eat only local plant-based food, '
            'use no electricity from fossil fuels, and offset any '
            'unavoidable emissions. The ultimate green challenge!'
        ),
    },
]


class Command(BaseCommand):
    """Seed the database with 12 pre-defined eco-challenges."""

    help = 'Seeds the database with 12 eco-challenges for users to participate in.'

    def handle(self, *args, **options):
        created_count = 0
        updated_count = 0

        for data in CHALLENGES_DATA:
            _, created = Challenge.objects.update_or_create(
                title=data['title'],
                defaults={
                    'icon': data['icon'],
                    'category': data['category'],
                    'difficulty': data['difficulty'],
                    'duration_days': data['duration_days'],
                    'carbon_save_potential': data['carbon_save_potential'],
                    'description': data['description'],
                    'is_active': True,
                },
            )
            if created:
                created_count += 1
            else:
                updated_count += 1

        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully seeded challenges: '
                f'{created_count} created, {updated_count} updated.'
            )
        )
