"""Management command to seed emission factors from default data."""
from django.core.management.base import BaseCommand
from calculator.models import EmissionFactor
from calculator.services import CarbonCalculatorService


class Command(BaseCommand):
    """Seed the EmissionFactor table from CarbonCalculatorService.DEFAULT_FACTORS."""
    help = 'Seeds the EmissionFactor table with default emission factors'

    def handle(self, *args, **options):
        """Execute the seed command."""
        created_count = 0
        updated_count = 0

        for category, subcategories in CarbonCalculatorService.DEFAULT_FACTORS.items():
            for sub_key, data in subcategories.items():
                _, created = EmissionFactor.objects.update_or_create(
                    category=category,
                    sub_category=sub_key,
                    defaults={
                        'factor': data['factor'],
                        'unit': data['unit'],
                        'description': data.get('desc', ''),
                        'source': 'EPA/DEFRA',
                    },
                )
                if created:
                    created_count += 1
                else:
                    updated_count += 1

        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully seeded emission factors: '
                f'{created_count} created, {updated_count} updated.'
            )
        )
